"""Create the object-storage bucket(s)."""

from botocore.exceptions import ClientError
from django.core.files.storage import storages
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the object-storage bucket(s) if missing."

    def add_arguments(self, parser):
        parser.add_argument("buckets", nargs="*", help="Defaults to the configured default-storage bucket.")

    def handle(self, *args, **options):
        # The configured backend already assembled endpoint, credentials and addressing
        # style from settings.STORAGES, so none of it has to be repeated here.
        storage = storages["default"]
        client = storage.connection.meta.client
        for bucket in options["buckets"] or [storage.bucket_name]:
            self._ensure(client, bucket)

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
