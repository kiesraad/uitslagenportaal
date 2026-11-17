import itertools
import json
import time
from collections import Counter
from pathlib import Path
from typing import NamedTuple

from django.core.management.base import BaseCommand, CommandError
from pypdf import PdfReader

from mainsite.utils.utils import parallel_map
from pv_ocr.management.commands.classify_pvs import PVS, collect_pdfs, display_path
from pv_ocr.utils.pv_classifier import MODELS, PDF_METADATA_KEYS, pv_model_short_form
from pv_ocr.utils.pv_toc import HEADER_FRACTION, VOTE_COUNT_CONTENTS, PageContent, PvDetermineTOC, TableOfContents

SHORT_FORMS = {pv_model_short_form(model): model for model in MODELS}


def pdf_model(path: Path) -> str | None:
    """The short form of the model in the PDF's /PvModel, which the classifier writes, or None."""
    metadata = PdfReader(path).metadata
    return metadata.get(PDF_METADATA_KEYS["model"]) if metadata else None


class Outcome(NamedTuple):
    toc: TableOfContents | None
    model: str | None
    # Why there is no table of contents: an error, or a skip for a missing or unknown /PvModel.
    error: str | None
    skipped: str | None
    seconds: float


def determine_timed(path: Path, header_fraction: float, model: str | None, no_model: bool) -> Outcome:
    """Determine the table of contents of one file, also in a worker process. The model is the given one, else the
    file's /PvModel, and a file without a known one is skipped; with no_model the file is read unrestricted."""
    start = time.perf_counter()
    toc, skipped, error = None, None, None
    try:
        if not model and not no_model:
            short_form = pdf_model(path)
            model = SHORT_FORMS.get(short_form)
            if not model:
                skipped = f"unknown /PvModel {short_form!r}" if short_form else "no /PvModel"
        if not skipped:
            toc = PvDetermineTOC(path, header_fraction, model).determine()
    except Exception as exc:
        error = repr(exc)
    return Outcome(toc, model, error, skipped, time.perf_counter() - start)


def compact(toc: TableOfContents) -> str:
    """One line: "1 cover | 2-3 table-of-contents | 12-13 candidate-votes lijst 3", merging equal neighbours."""
    parts = []
    entries = toc.entries
    for _, group in itertools.groupby(entries, key=lambda e: (e.content, e.list_number, e.list_number_inferred)):
        group = list(group)
        first, last = group[0], group[-1]
        pages = str(first.page) if first.page == last.page else f"{first.page}-{last.page}"
        # A "?" marks a list number inferred from the pages around it.
        lijst = f" lijst {first.list_number}{'?' if first.list_number_inferred else ''}" if first.list_number else ""
        parts.append(f"{pages} {first.content}{lijst}")
    return " | ".join(parts)


class Command(BaseCommand):
    help = (
        "POC: determine the table of contents of processen-verbaal from the header of each page with Tesseract. "
        "Writes nothing to the database. Needs Tesseract with Dutch language data, which the dev image has."
    )

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", type=Path, default=[PVS])
        parser.add_argument(
            "--glob",
            default="**/*.pdf",
            help='files to take from each directory, e.g. "*/GR2026/*.pdf" (default "**/*.pdf")',
        )
        parser.add_argument("--limit", type=int, default=25, help="read at most N files; 0 for all (default 25)")
        parser.add_argument("--sample", type=int, help="read N randomly chosen files instead of the first ones")
        parser.add_argument("--json", action="store_true", help="print the table of contents as JSON per file")
        parser.add_argument("--show-text", action="store_true", help="print the OCR text of pages not recognized")
        parser.add_argument(
            "--jobs", type=int, default=1, help="read N files at a time in worker processes (default 1)"
        )
        parser.add_argument(
            "--model", choices=sorted(MODELS), help="the model of every file, instead of the one in its /PvModel"
        )
        parser.add_argument(
            "--no-model", action="store_true", help="read every file unrestricted, without its /PvModel"
        )
        parser.add_argument(
            "--crop-fraction",
            type=float,
            default=HEADER_FRACTION,
            help=f"the share of each page, from the top, to read: above 0 up to 1 (default {HEADER_FRACTION})",
        )

    def handle(self, *args, **options):
        fraction = options["crop_fraction"]
        if not 0 < fraction <= 1:
            raise CommandError("--crop-fraction must be above 0 and at most 1")
        if options["model"] and options["no_model"]:
            raise CommandError("--model and --no-model cannot be combined")

        pdfs = collect_pdfs(options["paths"], options["glob"], options["limit"], options["sample"])

        contents, pages, vote_count_pages, seconds_total, errors, skipped = Counter(), 0, 0, 0.0, 0, 0
        with parallel_map(options["jobs"]) as run:
            args = (determine_timed, pdfs, itertools.repeat(fraction), itertools.repeat(options["model"]))
            args += (itertools.repeat(options["no_model"]),)
            for path, (toc, model, error, skip, seconds) in zip(pdfs, run(*args)):
                if skip:
                    self.stdout.write(f"{display_path(path)}  skipped: {skip}")
                    skipped += 1
                    continue
                seconds_total += seconds
                self.stdout.write(f"{display_path(path)}  {model or 'unrestricted'}  {seconds:.1f}s")
                if error:
                    self.stdout.write(f"  error {error}")
                    errors += 1
                    continue

                self.stdout.write("  " + (json.dumps(toc.to_json()) if options["json"] else compact(toc)))
                for entry in toc.entries:
                    contents[entry.content] += 1
                    if options["show_text"] and entry.content == PageContent.UNKNOWN:
                        self.stdout.write(f"    p{entry.page}: " + " ".join(entry.text.split())[:150])
                pages += len(toc.entries)
                found = sum(entry.content in VOTE_COUNT_CONTENTS for entry in toc.entries)
                vote_count_pages += found
                self.stdout.write(f"  {found} vote-count pages")

        self.stdout.write("")
        self.stdout.write(f"{'count':>5}  content")
        for content, count in contents.most_common():
            self.stdout.write(f"{count:>5}  {content}")
        unknown = contents[PageContent.UNKNOWN]
        self.stdout.write("")
        read = len(pdfs) - errors - skipped
        self.stdout.write(f"{pages} pages in {read} files, {skipped} skipped, {errors} errors")
        if pages:
            self.stdout.write(f"unknown: {unknown / pages:.0%}")
            self.stdout.write(f"vote-count pages: {vote_count_pages}")
            self.stdout.write(f"{seconds_total:.1f}s in total, {seconds_total / pages:.2f}s per page")
