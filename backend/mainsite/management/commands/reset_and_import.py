from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Wipe election data, seed the database, and import fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "folder",
            nargs="?",
            default=".data",
            help="Path to a fixture folder containing EML XML files (default: .data).",
        )

    def handle(self, *args, **options):
        folder = Path(options["folder"]).resolve()
        call_command("migrate")
        call_command("wipe_db")
        call_command("seed")
        call_command("import_election", str(folder))
