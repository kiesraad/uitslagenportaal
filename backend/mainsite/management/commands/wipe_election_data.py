from django.core.management.base import BaseCommand, CommandError

from election.election_config_importer import wipe_election_data
from election.models import ElectionConfig


class Command(BaseCommand):
    help = "Wipe election data of one election, but keep its config."

    def add_arguments(self, parser):
        parser.add_argument(
            "election_config",
            type=str,
            help="Identifier of the election config to wipe, e.g. GR2026.",
        )

    def handle(self, *args, **options):
        identifier = options["election_config"]
        try:
            election_config = ElectionConfig.with_expired.get(identifier=identifier)
        except ElectionConfig.DoesNotExist:
            raise CommandError(f"Election config does not exist: {identifier}")

        self.stdout.write(f"Wiping election data for {election_config.identifier}...")
        wipe_election_data(election_config)
        self.stdout.write(self.style.SUCCESS(f"Data for election config {election_config.identifier} wiped."))
