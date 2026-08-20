import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from eml_import.utils.folder_eml_importer import FolderEMLImporter


def default_workers() -> int:
    return max(1, (os.cpu_count() or 1))


class Command(BaseCommand):
    help = "Import an election fixture folder into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "folder",
            type=str,
            help="Path to a fixture folder containing EML XML files.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=default_workers(),
            help="Number of worker processes to import with (default: one per CPU). use 1 to import serially.",
        )

    def handle(self, *args, **options):
        folder = Path(options["folder"]).resolve()
        if not folder.is_dir():
            raise CommandError(f"Folder does not exist: {folder}")

        workers = options["workers"]
        if workers < 1:
            raise CommandError(f"--workers must be at least 1, got {workers}")

        start = time.time()
        FolderEMLImporter().import_folder(folder, workers=workers)
        self.stdout.write(self.style.SUCCESS(f"Processed {folder} in {time.time() - start:.1f} seconds"))
