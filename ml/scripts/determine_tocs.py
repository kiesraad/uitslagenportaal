import argparse
import json
import logging
from pathlib import Path

from dvc import api
from mainsite.utils.utils import parallel_map
from pv_ocr.management.commands.classify_pvs import collect_pdfs
from pv_ocr.management.commands.determine_pv_toc import pdf_model
from pv_ocr.utils.pv_classifier import MODELS, pv_model_short_form
from pv_ocr.utils.pv_toc import PvDetermineTOC, TableOfContents

SHORT_FORMS = {pv_model_short_form(model): model for model in MODELS}

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")
    parser.add_argument("output")
    return parser.parse_args()


def determine_toc(path: Path) -> TableOfContents | None:
    logger.info("Determine TOC for %s", path)
    try:
        short_form = pdf_model(path)
        if short_form is None:
            return None
        model = SHORT_FORMS.get(short_form)
        if not model:
            return None

        return PvDetermineTOC(path, model=model).determine()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s: %s", path, exc)
        return None


def main():
    """Write the table of contents of each PDF in `dir` to `output`, keyed by its path relative to `dir`; null for a
    PDF without a supported /PvModel or whose TOC failed."""
    params = api.params_show()
    args = get_args()
    root = Path(args.dir)
    pdfs = collect_pdfs([root], "**/*.pdf")

    with parallel_map(params["jobs"]) as run:
        tocs = {
            pdf.relative_to(root).as_posix(): toc.to_json() if toc else None
            for pdf, toc in zip(pdfs, run(determine_toc, pdfs))
        }

    Path(args.output).write_text(json.dumps(tocs, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
