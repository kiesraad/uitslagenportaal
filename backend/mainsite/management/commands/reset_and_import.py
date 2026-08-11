from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from mainsite.management.commands.import_election import default_workers


class Command(BaseCommand):
    help = "Wipe election data, seed the database, and import fixtures."

    def add_arguments(self, parser):
        parser.add_argument(
            "folder",
            nargs="?",
            default=".data",
            help="Path to a fixture folder containing EML XML files (default: .data).",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=default_workers(),
            help="Number of worker processes to import with (default: one per CPU).",
        )

    def handle(self, *args, **options):
        folder = Path(options["folder"]).resolve()
        call_command("wipe_db")
        call_command("seed")
        call_command("import_election", str(folder), workers=options["workers"])
