import argparse
import csv
import json
import logging
import re
from functools import partial
from pathlib import Path

import cv2
import numpy as np
from dvc import api
from file_import.utils.file_handler import build_xml_parser
from mainsite.utils.utils import parallel_map
from pv_ocr.management.commands.classify_pvs import collect_pdfs
from pv_ocr.utils.ocr import open_pdf, pdf_file, render_page
from pv_ocr.utils.pv_classifier import PDF_METADATA_KEYS
from pv_ocr.utils.pv_toc import LIST_CONTENTS, PageContent
from pv_ocr.utils.vote_tables import (
    BorderedTableDetector,
    Box,
    CountFieldDetector,
    GrayColumnDetector,
    is_blank,
    upright,
)
from pyeml_bindings import Eml510
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# The models whose counts are handwritten.
OCR_MODELS = {"N10-1", "N10-2", "Na14-1", "Na14-2-B1", "Na31-2-B1"}
# The first 510b holds the counts the gemeentelijk stembureau set, after its corrections (Na 14-1). Only a later
# recount (Na 14-2) corrects that 510b, in a `_correctie<n>`.
LATER_CORRECTION_MODELS = {"Na14-2-B1"}
CORRIGENDUM_MODELS = {"Na14-1", "Na14-2-B1"}
# The share of counts that are not 0 but blank above which a PV is left out; most PVs have none.
MAX_BLANK_SHARE = 0.1
# Gemeenten fill in the templates differently, so a candidate page tries each layout. Digit boxes are the more
# specific; where a page has both, the areas agree. Of the gray column levels, the one finding the most rows wins.
CANDIDATE_DETECTORS = [[BorderedTableDetector()], [GrayColumnDetector(), GrayColumnDetector(level=200)]]
COUNT_DETECTOR = CountFieldDetector()
CANDIDATES_PER_TABLE = 25

COUNT_REASONS = {
    "A": "geldige stempassen",
    "B": "geldige volmachtbewijzen",
    "C": "geldige kiezerspassen",
    "D": "toegelaten kiezers",
    "F": "blanco",
    "G": "ongeldig",
    "I": "meer getelde stembiljetten",
    "J": "minder getelde stembiljetten",
}
CSV_FIELDS = ["path", "pdf", "model", "page", "content", "field", "label", "blank", "changed"]


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("tocs", help="The JSON-file the toc stage wrote")
    parser.add_argument("output")
    parser.add_argument("--glob", default="**/*.pdf", help="The PDFs in `dir` to crop, for a trial run")
    parser.add_argument("--debug", help="Write each page with the found areas drawn on it to this directory")
    return parser.parse_args()


def eml_version(path: Path) -> int:
    """0 for the original 510b, n for `_correctie<n>`."""
    match = re.search(r"_correctie(\d+)\.eml\.xml$", path.name)
    return int(match.group(1)) if match else 0


def read_counts(path: Path, stembureau: str) -> dict[str, int] | None:
    """The counts of the stembureau in a 510b, keyed by field: `A`…`J`, `E.<list>` and `L<list>-<candidate>`."""
    eml = build_xml_parser().parse(path, Eml510)
    for contest in eml.count.election.contests.contest:
        for unit in contest.reporting_unit_votes:
            if str(unit.reporting_unit_identifier.id).endswith(f"::SB{stembureau}"):
                return unit_counts(unit)
    return None


def unit_counts(unit) -> dict[str, int]:
    counts = {}
    list_number = None
    for selection in unit.selection:
        if selection.affiliation_identifier:
            list_number = int(selection.affiliation_identifier.id)
            counts[f"E.{list_number}"] = selection.valid_votes
        elif selection.candidate:
            counts[f"L{list_number}-{int(selection.candidate.candidate_identifier.id)}"] = selection.valid_votes
    reasons = {votes.reason_code.value: votes.value for votes in [*unit.rejected_votes, *unit.uncounted_votes]}
    counts |= {field: reasons[code] for field, code in COUNT_REASONS.items() if code in reasons}
    counts["E"] = unit.total_counted
    counts["H"] = unit.total_counted + reasons.get("blanco", 0) + reasons.get("ongeldig", 0)
    return counts


def count_fields(content: PageContent, counts: dict[str, int]) -> list[str]:
    """The fields of a count page, top to bottom."""
    match content:
        case PageContent.ADMITTED_VOTERS:
            return [field for field in "ABCD" if field in counts]
        case PageContent.VOTES_CAST:
            lists = sorted(int(field[2:]) for field in counts if field.startswith("E."))
            return [f"E.{number}" for number in lists] + ["E", "F", "G", "H"]
        case PageContent.DIFFERENCES:
            return ["I", "J"]
    return []


def page_areas(
    gray: np.ndarray, entry: dict, tables_before: int, counts: dict, model: str
) -> tuple[np.ndarray, list[tuple[str, Box]], int]:
    """The deskewed page, the field and area of each number on it, and the number of candidate tables; no areas when
    the page doesn't match."""
    content = PageContent(entry["content"])
    if content in LIST_CONTENTS:
        for detectors in CANDIDATE_DETECTORS:
            found = [detector.detect(gray) for detector in detectors]
            deskewed, tables = max(found, key=lambda result: sum(map(len, result[1])))
            if tables:
                break
        gray = deskewed
        # The right-hand table holds the next candidates, also when the left one is not found.
        columns = [int(table[0][0] > 0.6 * gray.shape[1]) for table in tables]
        areas = [
            (f"L{entry['list_number']}-{(tables_before + column) * CANDIDATES_PER_TABLE + row}", area)
            for column, table in zip(columns, tables)
            for row, area in enumerate(table, 1)
        ]
        # Rows past the last candidate are empty.
        return gray, [(field, area) for field, area in areas if field in counts], max(columns, default=-1) + 1

    fields = count_fields(content, counts)
    # Only a later recount prints the original counts next to the fields.
    areas = COUNT_DETECTOR.detect(gray, fields, originals=model in LATER_CORRECTION_MODELS)
    # I and J differ in one word, méér or minder; one found alone may well be the other.
    if content == PageContent.DIFFERENCES and len(areas) < len(fields):
        areas = []
    if len(areas) < len(fields):
        logger.info("Page %s: counts %s not found", entry["page"], sorted(set(fields) - {field for field, _ in areas}))
    return gray, areas, 0


def draw(gray: np.ndarray, areas: list[tuple[str, Box]]) -> np.ndarray:
    image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for field, (x, y, w, h) in areas:
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(image, field, (x + 4, y + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
    return image


def extract(pdf: Path, toc: list[dict] | None, root: Path, output: Path, debug: Path | None) -> list[dict]:
    """Write the crop of each number on the vote pages of the PDF, and return its rows for the CSV."""
    relative = pdf.relative_to(root).as_posix()
    try:
        metadata = PdfReader(pdf).metadata or {}
        model = metadata.get(PDF_METADATA_KEYS["model"])
        if model not in OCR_MODELS or not toc:
            return []
        stembureau = metadata[PDF_METADATA_KEYS["stembureau"]]
        emls = sorted(pdf.parent.glob("*.eml.xml"), key=eml_version)
        if not emls:
            logger.warning("%s: no 510b", relative)
            return []
        later = model in LATER_CORRECTION_MODELS
        counts = read_counts(emls[-1] if later else emls[0], stembureau)
        # A corrigendum is only filled in where it differs from the original.
        original = read_counts(emls[0], stembureau) if later and len(emls) > 1 else None
        if counts is None:
            logger.warning("%s: stembureau %s not in %s", relative, stembureau, emls[-1].name)
            return []

        rows, crops, skipped, list_tables = [], [], [], {}
        crop_dir = output / pdf.relative_to(root).with_suffix("")
        with open_pdf(pdf_file(pdf)) as document:
            for entry in toc:
                content = PageContent(entry["content"])
                list_number = entry.get("list_number")
                if content in LIST_CONTENTS:
                    if not list_number:
                        continue
                elif not count_fields(content, counts):
                    continue

                image = render_page(document[entry["page"] - 1])
                if image is None:
                    continue
                # A list continues on the next page with its next table of candidates. A PV can also hold a list
                # twice; a new list page starts over when the list has no more candidates to continue with.
                tables_before = list_tables.get(list_number, 0)
                if (
                    content == PageContent.CANDIDATE_VOTES
                    and f"L{list_number}-{tables_before * CANDIDATES_PER_TABLE + 1}" not in counts
                ):
                    tables_before = 0
                gray, areas, tables = page_areas(upright(np.asarray(image)), entry, tables_before, counts, model)
                if list_number:
                    list_tables[list_number] = tables_before + tables
                if not areas:
                    skipped.append(entry["page"])
                    continue
                if debug:
                    cv2.imwrite(str(debug / f"{pdf.stem}_p{entry['page']}.png"), draw(gray, areas))
                for field, (x, y, w, h) in areas:
                    path = crop_dir / f"p{entry['page']}_{field}.png"
                    crop = gray[y : y + h, x : x + w]
                    crops.append((path, crop))
                    rows.append(
                        {
                            "path": path.relative_to(output).as_posix(),
                            "pdf": relative,
                            "model": model,
                            "page": entry["page"],
                            "content": entry["content"],
                            "field": field,
                            "label": counts[field],
                            "blank": is_blank(crop),
                            "changed": "" if original is None else counts[field] != original.get(field),
                        }
                    )
        # Where many counts are blank that the 510b says are not, the PV was matched to the wrong stembureau, or its
        # pages to the wrong model. A corrigendum leaves unchanged counts blank, so cannot tell.
        if not later and model not in CORRIGENDUM_MODELS:
            nonzero = [row for row in rows if row["label"]]
            if len(nonzero) >= 10 and sum(row["blank"] for row in nonzero) > MAX_BLANK_SHARE * len(nonzero):
                logger.warning("%s: too many blank counts that are not 0, left out", relative)
                return []
        crop_dir.mkdir(parents=True, exist_ok=True)
        for path, crop in crops:
            cv2.imwrite(str(path), crop)
        logger.info("%s: %d crops, pages skipped: %s", relative, len(rows), skipped or "none")
        return rows
    except Exception as exc:  # noqa: BLE001
        logger.error("%s: %s", relative, exc)
        return []


def main():
    """Crop each handwritten number on the vote pages of the OCR models in `dir` into `output`, with `crops.csv`
    listing each crop and its value in the 510b."""
    params = api.params_show()
    args = get_args()
    root, output = Path(args.dir), Path(args.output)
    debug = Path(args.debug) if args.debug else None
    if debug:
        debug.mkdir(parents=True, exist_ok=True)
    tocs = json.loads(Path(args.tocs).read_text())
    pdfs = collect_pdfs([root], args.glob)
    output.mkdir(parents=True, exist_ok=True)

    with parallel_map(params["jobs"]) as run:
        found = run(
            partial(extract, root=root, output=output, debug=debug),
            pdfs,
            [tocs.get(pdf.relative_to(root).as_posix()) for pdf in pdfs],
        )
        with (output / "crops.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, CSV_FIELDS)
            writer.writeheader()
            for rows in found:
                writer.writerows(rows)


if __name__ == "__main__":
    main()
