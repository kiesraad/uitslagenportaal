from dataclasses import fields
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from pv_scraper.utils.pv_classifier import PvClassifier

PVS = settings.BASE_DIR / ".data" / "PVs"


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
