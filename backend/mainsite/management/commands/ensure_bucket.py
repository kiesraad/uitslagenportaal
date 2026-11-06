"""Create the object-storage bucket(s)."""

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import storages
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the object-storage bucket(s) if missing."

    def handle(self, *args, **options):
        # Create the bucket for each configured S3 storage
        for name in ("default", "pv_import"):
            storage = storages[name]
            if not hasattr(storage, "bucket_name"):
                continue

            client = storage.connection.meta.client
            self._ensure(client, storage.bucket_name)
            if name == "default":
                self._allow_frontend_reads(client, storage.bucket_name)

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

    def _allow_frontend_reads(self, client, bucket: str) -> None:
        # The PDF viewer fetches documents from the browser, so the bucket must answer the frontend's origin.
        client.put_bucket_cors(
            Bucket=bucket,
            CORSConfiguration={
                "CORSRules": [{"AllowedOrigins": settings.CORS_ALLOWED_ORIGINS, "AllowedMethods": ["GET"]}]
            },
        )
