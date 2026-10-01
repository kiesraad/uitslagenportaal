import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from eml_import.utils.folder_pdf_file_handler import FolderPDFFileHanlder


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

    def handle(self, *args, **options):
        folder = Path(options["folder"]).resolve()
        if not folder.is_dir():
            raise CommandError(f"Folder does not exist: {folder}")

        start = time.time()
        FolderPDFFileHanlder(folder).run()
        self.stdout.write(self.style.SUCCESS(f"Processed {folder} in {time.time() - start:.1f} seconds"))
