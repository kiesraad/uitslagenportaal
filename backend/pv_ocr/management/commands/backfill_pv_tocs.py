import sys
import time

from django.core.management.base import BaseCommand
from django.db.models import Q

from election.models import ElectionDocument
from pv_ocr.tasks import determine_document_toc
from pv_ocr.utils.pv_toc import pv_model
from pv_ocr.utils.toc_schema import TOC_VERSION


class Command(BaseCommand):
    help = "Determine the table of contents of every current PV of a supported model that has none, or an outdated one."

    def add_arguments(self, parser):
        parser.add_argument("--run-sync", action="store_true", help="run each task here instead of queueing it")

    def handle(self, *args, **options):
        file_types = [file_type for file_type in ElectionDocument.FileType if pv_model(file_type)]
        outdated = Q(toc__isnull=True) | Q(toc__version__lt=TOC_VERSION)
        document_ids = ElectionDocument.objects.filter(outdated, file_type__in=file_types).values_list("pk", flat=True)
        start = time.monotonic()
        count = 0
        verb = "Determined" if options["run_sync"] else "Queued"
        try:
            for document_id in document_ids.order_by("pk").iterator():
                if options["run_sync"]:
                    determine_document_toc(document_id)
                else:
                    determine_document_toc.delay(document_id)
                count += 1
        except KeyboardInterrupt:
            # Each TOC is saved as it is determined, so a new run goes on where this one stopped.
            elapsed = time.monotonic() - start
            self.stdout.write(
                self.style.WARNING(f"Interrupted. {verb} the table of contents of {count} PV(s) in {elapsed:.1f} s")
            )
            sys.exit(130)
        elapsed = time.monotonic() - start
        self.stdout.write(self.style.SUCCESS(f"{verb} the table of contents of {count} PV(s) in {elapsed:.1f} s"))
