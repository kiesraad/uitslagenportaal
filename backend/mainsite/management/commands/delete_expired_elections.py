from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from election.models import ElectionConfig, ElectionDocument, deletion_cutoff


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
        expired = ElectionConfig.objects.filter(date__lt=cutoff).order_by("date")

        if not expired.exists():
            self.stdout.write(f"No elections started before {cutoff:%Y-%m-%d %H:%M}. Nothing to delete.")
            return

        self.stdout.write(f"Elections that started before {cutoff:%Y-%m-%d %H:%M}:")
        for config in expired:
            self.stdout.write(f"  {config.identifier} ({config.label}) started {config.date:%Y-%m-%d}")

        # Collect the storage keys before deleting: the rows carry the only
        # reference to the stored objects, so afterwards they are unreachable.
        storage_keys = list(
            ElectionDocument.objects.filter(
                region__election__election_config__in=expired,
            ).values_list("storage_key", flat=True)
        )

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run: would delete {expired.count()} election(s) and {len(storage_keys)} stored document(s)."
                )
            )
            self.stdout.write("Re-run with --confirm to apply.")
            return

        # Delete the database rows first. If that fails the transaction rolls
        # back and the stored objects are still referenced; the reverse order
        # would leave rows pointing at files that no longer exist.
        with transaction.atomic():
            _, summary = expired.delete()

        self.stdout.write(self.style.SUCCESS("Deleted from the database:"))
        for label, count in sorted(summary.items()):
            if count:
                self.stdout.write(f"  {label}: {count}")

        deleted, failed = self._delete_stored_documents(storage_keys)
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} object(s) from storage."))
        if failed:
            self.stdout.write(
                self.style.WARNING(f"{len(failed)} object(s) could not be deleted and are now orphaned in the bucket:")
            )
            for key, error in failed:
                self.stdout.write(f"  {key}: {error}")

    def _delete_stored_documents(self, storage_keys):
        """Remove objects from storage, reporting failures instead of raising.

        The database rows are already gone by this point, so one unreachable
        object must not abort the rest of the cleanup.
        """
        deleted = 0
        failed = []
        for key in storage_keys:
            try:
                default_storage.delete(key)
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed.append((key, exc))
            else:
                deleted += 1
        return deleted, failed
