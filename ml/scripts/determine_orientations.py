import argparse
import json
import logging
from functools import partial
from pathlib import Path

import numpy as np
from dvc import api
from mainsite.utils.utils import parallel_map
from pv_ocr.management.commands.classify_pvs import collect_pdfs
from pv_ocr.management.commands.determine_pv_toc import pdf_model
from pv_ocr.utils.ocr import open_pdf, pdf_file, render_page
from pv_ocr.utils.orientation import rotation
from pv_ocr.utils.pv_toc import LIST_CONTENTS, VOTE_COUNT_CONTENTS, PageContent

from scripts.ocr_models import OCR_MODELS

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("tocs", help="The JSON-file the toc stage wrote")
    parser.add_argument("output")
    parser.add_argument("--glob", default="**/*.pdf", help="The PDFs in `dir` to do, for a trial run")
    return parser.parse_args()


def oriented_pages(toc: list[dict]) -> list[int]:
    """The pages `extract_crops` turns upright, whatever the 510b holds."""
    pages = []
    for entry in toc:
        content = PageContent(entry["content"])
        if content in LIST_CONTENTS:
            selected = bool(entry.get("list_number"))
        elif content == PageContent.UNKNOWN:
            selected = entry["page"] >= len(toc) - 1
        else:
            selected = content in VOTE_COUNT_CONTENTS
        if selected:
            pages.append(entry["page"])
    return pages


def determine_orientations(pdf: Path, toc: list[dict] | None, root: Path) -> dict[str, int] | None:
    """The clockwise turn that puts each selected page upright, by page number."""
    relative = pdf.relative_to(root).as_posix()
    try:
        if pdf_model(pdf) not in OCR_MODELS or not toc:
            return None
        rotations = {}
        with open_pdf(pdf_file(pdf)) as document:
            for page in oriented_pages(toc):
                if (image := render_page(document[page - 1])) is not None:
                    rotations[str(page)] = rotation(np.asarray(image))
        logger.info("%s: %d pages", relative, len(rotations))
        return rotations
    except Exception as exc:  # noqa: BLE001
        logger.error("%s: %s", relative, exc)
        return None


def main():
    """Write the rotation of each page of the OCR models in `dir` that `extract_crops` turns upright to `output`, keyed
    by the path of its PDF relative to `dir` and its page number."""
    params = api.params_show()
    args = get_args()
    root = Path(args.dir)
    tocs = json.loads(Path(args.tocs).read_text())
    pdfs = collect_pdfs([root], args.glob)
    relatives = [pdf.relative_to(root).as_posix() for pdf in pdfs]

    with parallel_map(params["jobs"]) as run:
        found = run(partial(determine_orientations, root=root), pdfs, [tocs.get(relative) for relative in relatives])
        orientations = {relative: rotations for relative, rotations in zip(relatives, found) if rotations is not None}

    Path(args.output).write_text(json.dumps(orientations, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
