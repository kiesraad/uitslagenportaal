import time
from dataclasses import fields
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from pv_scraper.utils.pv_classifier import ClassificationResult, PvClassifier

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
    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="*", type=Path, default=[PVS])

    def handle(self, *args, **options):
        for path in options["paths"]:
            self.stdout.write(f"Classifying {path}...")
            result = PvClassifier(path).classify()
            if result is None:
                self.stdout.write("Classification failed")

            self.stdout.write("Result:")
            for field in fields(result.__class__):
                self.stdout.write(f"\t{field.name}: {getattr(result, field.name)}")
