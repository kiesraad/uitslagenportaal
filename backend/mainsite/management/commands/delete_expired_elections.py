from django.core.management.base import BaseCommand
from django.db import transaction

from election.election_config_storage import remove_expired_election_configs
from election.models import ElectionConfig, ElectionDocument
from election.utils import delete_stored_documents, deletion_cutoff, folder_prefixes


class Command(BaseCommand):
    help = (
        "Permanently delete elections that are past the deletion cutoff, "
        "including their stored documents. Runs as a dry run unless --confirm is passed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually delete. Without this flag the command only reports what would be removed.",
        )

    def handle(self, *args, **options):
        cutoff = deletion_cutoff()
        expired = ElectionConfig.with_expired.filter(date__lt=cutoff).order_by("date")

        if not expired.exists():
            self.stdout.write(f"No elections started before {cutoff:%Y-%m-%d %H:%M}. Nothing to delete.")
            return

        self.stdout.write(f"Elections that started before {cutoff:%Y-%m-%d %H:%M}:")
        for config in expired:
            self.stdout.write(f"  {config.identifier} ({config.label}) started {config.date:%Y-%m-%d}")

        # Collect the storage keys before deleting: the rows carry the only
        # reference to the stored objects, so afterwards they are unreachable.
        storage_keys = list(
            ElectionDocument.all_objects.filter(
                region__election__election_config__in=expired,
            ).values_list("storage_key", flat=True)
        )
        prefixes = folder_prefixes(storage_keys)

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run: would delete {expired.count()} election(s) and {len(storage_keys)} stored document(s)"
                    f" across {len(prefixes)} folder(s): {', '.join(sorted(prefixes)) or '-'}."
                )
            )
            self.stdout.write("Re-run with --confirm to apply.")
            return

        # Remove the expired config files in the object storage before removing the DB rows,
        # so import_new_election_configs won't import it during deletion
        removed_config_files = remove_expired_election_configs([config.identifier for config in expired])
        self.stdout.write(self.style.SUCCESS("Deleted config files from object storage:"))
        for file in removed_config_files:
            self.stdout.write(f"  {file}")

        # Delete the database rows first. If that fails the transaction rolls
        # back and the stored objects are still referenced; the reverse order
        # would leave rows pointing at files that no longer exist.
        with transaction.atomic():
            _, summary = expired.delete()

        self.stdout.write(self.style.SUCCESS("Deleted from the database:"))
        for label, count in sorted(summary.items()):
            if count:
                self.stdout.write(f"  {label}: {count}")

        deleted, failed = delete_stored_documents(storage_keys, prefixes)
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} object(s) from storage."))
        if failed:
            self.stdout.write(
                self.style.WARNING(f"{len(failed)} object(s) could not be deleted and are now orphaned in the bucket:")
            )
            for key, error in failed:
                self.stdout.write(f"  {key}: {error}")
