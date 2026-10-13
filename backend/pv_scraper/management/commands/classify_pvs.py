import multiprocessing
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from pathlib import Path

import django
from django.conf import settings
from django.core.management.base import BaseCommand

from pv_scraper.utils.pv_classifier import BASES, MODELS, ClassificationResult, PvClassificationException, PvClassifier

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


def classify_timed(path: Path) -> tuple[ClassificationResult | None, str, str | None, float]:
    """Classify one file, also in a worker process: the result and its storage name, or the error, and the seconds it
    took. The name is empty when the PV doesn't give enough to name it."""
    start = time.perf_counter()
    result, name, error = None, "", None
    try:
        classifier = PvClassifier(path)
        result = classifier.classify()
        if result and result.matched_on.is_certain():
            name = classifier.storage_name()
    except PvClassificationException:
        pass
    except Exception as exc:
        result, error = None, repr(exc)
    return result, name, error, time.perf_counter() - start


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
        # "storage name" is what the PV would be stored as, from what it says alone; "from" tells where its election
        # was read: the header, elsewhere in the PDF, or the file name.
        row = "{:<18} {:<10} {:<8} {:<17} {:<48} {:<6} {:<10} {:<9} {:<7} {:>6}  {}"
        header = row.format(
            "model",
            "basis",
            "code",
            "title",
            "storage name",
            "from",
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
        # Workers don't inherit Django's setup, which unpickling a task needs because the classifier imports models.
        # Results come back in input order, so a slow file holds back the rows after it.
        executor = (
            ProcessPoolExecutor(jobs, mp_context=multiprocessing.get_context("spawn"), initializer=django.setup)
            if jobs > 1
            else nullcontext()
        )
        with executor as pool:
            outcomes = pool.map(classify_timed, pdfs) if pool else map(classify_timed, pdfs)
            result: ClassificationResult
            for path, (result, name, error, seconds) in zip(pdfs, outcomes):
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
                            f"{seconds:.1f}s",
                            f"{display_path(path)}  {error}",
                        )
                    )
                    models["error"] += 1
                    continue

                assert result is not None
                # A model read from its code alone is shown with a question mark.
                model = f"{result.model}?" if result.matched_on == "code" else result.model or "-"
                election = result.election
                self.stdout.write(
                    row.format(
                        model,
                        result.matched_on,
                        result.codes[0] if result.codes else "",
                        "/".join(result.titles),
                        name or "-",
                        election.found_in,
                        result.region.stembureau,
                        result.region.kieskring,
                        result.found_by,
                        f"{seconds:.1f}s",
                        display_path(path),
                    )
                )
                if result.matched_on not in ("code+title", "title") and options["show_text"]:
                    self.stdout.write("    " + " ".join(result.text.split())[:300])
                models[model] += 1
                bases[result.matched_on] += 1
                elections[" ".join(filter(None, [election.id or "-", election.found_in, election.authority]))] += 1

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
