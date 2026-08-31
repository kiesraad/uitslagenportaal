"""Create the object-storage bucket(s) and optionally make their objects publicly readable."""

import json

from botocore.exceptions import ClientError
from django.core.files.storage import storages
from django.core.management.base import BaseCommand


# Anonymous GetObject on the contents, plus location/list on the bucket itself.
def _public_read_policy(bucket: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            },
        ],
    }


class Command(BaseCommand):
    help = "Create the object-storage bucket(s) if missing and optionally make their objects publicly readable."

    def add_arguments(self, parser):
        parser.add_argument("buckets", nargs="*", help="Defaults to the configured default-storage bucket.")
        # Opt-in: a bucket only becomes world-readable when something asks for it.
        parser.add_argument("--public", action="store_true", help="Grant anonymous read access to the objects.")

    def handle(self, *args, **options):
        # The configured backend already assembled endpoint, credentials and addressing
        # style from settings.STORAGES, so none of it has to be repeated here.
        storage = storages["default"]
        client = storage.connection.meta.client
        for bucket in options["buckets"] or [storage.bucket_name]:
            self._ensure(client, bucket, public=options["public"])

    def _ensure(self, client, bucket: str, public: bool) -> None:
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            # HEAD has no body, so botocore surfaces the bare status for a missing bucket.
            if exc.response["Error"]["Code"] not in ("404", "NotFound", "NoSuchBucket"):
                raise
            client.create_bucket(Bucket=bucket)
            self.stdout.write(f"Created bucket {bucket}")
        if public:
            # Unconditional, so a drifted policy is repaired rather than left alone.
            client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(_public_read_policy(bucket)))
        self.stdout.write(self.style.SUCCESS(f"Bucket {bucket} ready"))
