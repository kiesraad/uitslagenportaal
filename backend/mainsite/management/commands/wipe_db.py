from django.core.management.base import BaseCommand
from django.db import transaction

from election.models import ElectionConfig
from eml_import.models import ImportedEmlHash


class Command(BaseCommand):
    help = "Remove all election data from the database."

    def handle(self, *args, **options):
        with transaction.atomic():
            _, summary = ElectionConfig.with_expired.all().delete()
            _, hash_summary = ImportedEmlHash.objects.all().delete()
            summary = {**summary, **hash_summary}

        self.stdout.write(self.style.SUCCESS("Election data wiped."))
        for label, count in sorted(summary.items()):
            if count:
                self.stdout.write(f"  {label}: {count}")
