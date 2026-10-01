import time

from django.core.files.storage import storages
from django.core.management.base import BaseCommand

from eml_import.utils.pdf_file_handler import PDFFileHandler


class Command(BaseCommand):
    help = "Import proces-verbaal PDFs from the pv_import storage."

    def handle(self, *args, **options):
        storage = storages["pv_import"]
        start = time.time()
        count = PDFFileHandler(storage).run()
        elapsed = time.time() - start
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {count} proces-verbaal PDF(s) from {storage.location} in {elapsed:.1f} seconds"
            )
        )
