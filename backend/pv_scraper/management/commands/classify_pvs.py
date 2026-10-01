import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from pv_scraper.utils.pv_classifier import BASES, MODELS, ClassificationResult, PvClassifier

PVS = settings.BASE_DIR / ".data" / "PVs"


def display_path(path: Path) -> str:
    path, root = path.resolve(), PVS.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def collect_pdfs(paths: list[Path], pattern: str) -> list[Path]:
    """Files as given, and in each directory the files matching the glob pattern."""
    pdfs = []
    for path in paths:
        if path.is_dir():
            pdfs.extend(p for p in sorted(path.glob(pattern)) if "_tools" not in p.parts)
        else:
            pdfs.append(path)
    return pdfs


def classify_timed(path: Path) -> tuple[ClassificationResult | None, str | None, float]:
    """Classify one file, also in a worker process: the result or the error, and the seconds it took."""
    start = time.perf_counter()
    try:
        result, error = PvClassifier(path).classify(), None
    except Exception as exc:
        result, error = None, repr(exc)
    return result, error, time.perf_counter() - start


class Command(BaseCommand):
    help = (
        "POC: classify processen-verbaal by model, region and election with Tesseract, and print a row per file. "
        "Needs Tesseract with Dutch language data, which the dev image has."
    )

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", type=Path, default=[PVS])
        parser.add_argument(
            "--glob",
            default="**/*.pdf",
            help='files to take from each directory, e.g. "*/GR2026/*.pdf" (default "**/*.pdf")',
        )
        parser.add_argument("--limit", type=int, default=25, help="classify at most N files; 0 for all (default 25)")
        parser.add_argument("--sample", type=int, help="classify N randomly chosen files instead of the first ones")
        parser.add_argument("--show-text", action="store_true", help="print the OCR text of files not identified")
        parser.add_argument(
            "--jobs", type=int, default=1, help="classify N files at a time in worker processes (default 1)"
        )

    def handle(self, *args, **options):
        pdfs = collect_pdfs(options["paths"], options["glob"])
        if options["sample"]:
            pdfs = random.Random(0).sample(pdfs, min(options["sample"], len(pdfs)))
        elif options["limit"]:
            pdfs = pdfs[: options["limit"]]

        # Rows are printed as each file is done, so the columns have fixed widths and the file name goes last.
        # "model" is the verdict; "code" and "title" show what OCR found on the page.
        # "election" comes from the PDF, or from the file name when "from" says so.
        row = "{:<18} {:<10} {:<8} {:<17} {:<8} {:<4} {:<8} {:<10} {:<9} {:<7} {:>6}  {}"
        header = row.format(
            "model",
            "basis",
            "code",
            "title",
            "election",
            "from",
            "gemeente",
            "stembureau",
            "kieskring",
            "pass",
            "time",
            "file",
        )
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        jobs = options["jobs"]
        models, bases, elections = Counter(), Counter(), Counter()
        if jobs > 1:
            # Tesseract's own threads compete with the workers; one each is about 1.6x faster with 4 jobs.
            os.environ["OMP_THREAD_LIMIT"] = "1"
        # Results come back in input order, so a slow file holds back the rows after it.
        with ProcessPoolExecutor(jobs) if jobs > 1 else nullcontext() as pool:
            outcomes = pool.map(classify_timed, pdfs) if pool else map(classify_timed, pdfs)
            result: ClassificationResult
            for path, (result, error, seconds) in zip(pdfs, outcomes):
                if error:
                    self.stdout.write(
                        row.format(
                            "error",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            f"{seconds:.1f}s",
                            f"{display_path(path)}  {error}",
                        )
                    )
                    models["error"] += 1
                    continue

                assert result is not None
                # A model read from its code alone is shown with a question mark.
                model = f"{result.model}?" if result.matched_on == "code" else result.model or "-"
                election, election_from = result.election
                self.stdout.write(
                    row.format(
                        model,
                        result.matched_on,
                        result.codes[0] if result.codes else "",
                        "/".join(result.titles),
                        election or "-",
                        election_from,
                        result.region.get("gemeente", ""),
                        result.region.get("stembureau", ""),
                        result.region.get("kieskring", ""),
                        result.found_by,
                        f"{seconds:.1f}s",
                        display_path(path),
                    )
                )
                if result.matched_on not in ("code+title", "title") and options["show_text"]:
                    self.stdout.write("    " + " ".join(result.text.split())[:300])
                models[model] += 1
                bases[result.matched_on] += 1
                elections[f"{election or '-'} {election_from}".strip()] += 1

        summary = "{:>5}  {:<18} {}"
        self.stdout.write("")
        self.stdout.write(summary.format("count", "model", "description"))
        for model, count in models.most_common():
            self.stdout.write(summary.format(count, model, MODELS.get(model.rstrip("?"), "")))
        self.stdout.write("")
        self.stdout.write(summary.format("count", "basis", ""))
        for basis in BASES:
            if bases[basis]:
                self.stdout.write(summary.format(bases[basis], basis, ""))
        self.stdout.write("")
        self.stdout.write(summary.format("count", "election", ""))
        for election, count in sorted(elections.items()):
            self.stdout.write(summary.format(count, election, ""))
