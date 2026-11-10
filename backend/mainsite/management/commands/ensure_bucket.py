"""Create the object-storage bucket(s)."""

from botocore.exceptions import ClientError
from django.core.files.storage import storages
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the object-storage bucket(s) if missing."

    def handle(self, *args, **options):
        # Create the bucket for each configured S3 storage
        for storage in [storages["default"], storages["pv_import"]]:
            if not hasattr(storage, "bucket_name"):
                continue

            client = storage.connection.meta.client
            self._ensure(client, storage.bucket_name)

    def _ensure(self, client, bucket: str) -> None:
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            # HEAD has no body, so botocore surfaces the bare status for a missing bucket.
            if exc.response["Error"]["Code"] not in ("404", "NotFound", "NoSuchBucket"):
                raise
            client.create_bucket(Bucket=bucket)
            self.stdout.write(f"Created bucket {bucket}")
        self.stdout.write(self.style.SUCCESS(f"Bucket {bucket} ready"))
