from dataclasses import fields
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from pv_scraper.utils.pv_classifier import PvClassifier


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+", type=Path)

    def handle(self, *args, **options):
        # Folders are for classify_pvs.
        for path in options["paths"]:
            if not path.is_file() or path.suffix.lower() != ".pdf":
                raise CommandError(f"{path} is not a PDF file")

        for path in options["paths"]:
            self.stdout.write(f"Classifying {path}...")
            result = PvClassifier(path).classify()
            if result is None:
                self.stdout.write("Classification failed")
                continue

            self.stdout.write("Result:")
            for field in fields(result.__class__):
                self.stdout.write(f"\t{field.name}: {getattr(result, field.name)}")
