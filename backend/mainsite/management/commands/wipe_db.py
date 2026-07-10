from django.core.management.base import BaseCommand
from django.db import transaction

from election.models import ElectionConfig


class Command(BaseCommand):
    help = "Remove all election data from the database."

    def handle(self, *args, **options):
        with transaction.atomic():
            _, summary = ElectionConfig.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Election data wiped."))
        for label, count in sorted(summary.items()):
            if count:
                self.stdout.write(f"  {label}: {count}")
