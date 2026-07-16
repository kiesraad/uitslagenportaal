from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from mainsite.utils.election_importer import ElectionImporter


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

        ElectionImporter(folder).run()
