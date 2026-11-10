from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from redis.exceptions import LockError

from election.election_config_importer import WIPE_LOCK_WAIT, wipe_election_data
from election.models import ElectionConfig
from eml_import.utils.github_eml_file_handler import LOCK_TIMEOUT, GithubEmlFileHandler


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

        self.stdout.write(f"Waiting until no import task is running for {identifier} (max {WIPE_LOCK_WAIT} s)...")
        # The same lock the commit imports take, so none runs against a half-wiped election
        lock = cache.lock(
            GithubEmlFileHandler.cache_lock_key(identifier), timeout=LOCK_TIMEOUT, blocking_timeout=WIPE_LOCK_WAIT
        )
        if not lock.acquire():
            raise CommandError(f"Commits are still being imported for election config {identifier}")

        try:
            self.stdout.write(f"Wiping election data for {identifier}...")
            wipe_election_data(election_config)
        finally:
            try:
                lock.release()
            except LockError:
                self.stderr.write(f"Lock for {identifier} expired while wiping election data")
        self.stdout.write(self.style.SUCCESS(f"Data for election config {identifier} wiped."))
