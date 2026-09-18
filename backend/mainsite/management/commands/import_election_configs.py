from django.core.management.base import BaseCommand

from election.election_config_storage import import_new_election_configs


class Command(BaseCommand):
    help = "Import new or changed election_config JSON files from object storage (election_configs/*.json)."

    def handle(self, *args, **options):
        imported = import_new_election_configs()
        if imported:
            self.stdout.write(self.style.SUCCESS(f"Imported {imported} election config(s)."))
        else:
            self.stdout.write("No new or changed election configs found.")
