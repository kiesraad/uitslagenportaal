from django.core.management.base import BaseCommand, CommandError

from election.models import ElectionConfig
from eml_import.utils.github_eml_file_handler import GithubEmlFileHandler


class Command(BaseCommand):
    help = "Import all remaining commits from GitHub."

    def add_arguments(self, parser):
        parser.add_argument(
            "election_config",
            type=str,
            help="Identifier of the election config to import, e.g. GR2026.",
        )

    def handle(self, *args, **options):
        identifier = options["election_config"]
        try:
            election_config = ElectionConfig.with_expired.get(identifier=identifier)
        except ElectionConfig.DoesNotExist:
            raise CommandError(f"Election config does not exist: {identifier}")

        file_cnt = GithubEmlFileHandler(election_config).run()
        self.stdout.write(self.style.SUCCESS(f"Processed {file_cnt} file(s)."))
