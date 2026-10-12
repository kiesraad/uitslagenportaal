from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from django.core.files.storage import InMemoryStorage
from django.core.management import call_command

from mainsite.management.commands import ensure_bucket


def s3_storage(bucket: str, head_error: str | None = None) -> MagicMock:
    """A stand-in for an S3 storage, whose bucket lookup fails with the given error code."""
    storage = MagicMock(bucket_name=bucket)
    if head_error:
        error = ClientError({"Error": {"Code": head_error}}, "HeadBucket")
        storage.connection.meta.client.head_bucket.side_effect = error
    return storage


def run_ensure_bucket(default, pv_import) -> None:
    with patch.object(ensure_bucket, "storages", {"default": default, "pv_import": pv_import}):
        call_command("ensure_bucket")


def test_creates_the_missing_bucket_of_each_storage():
    default = s3_storage("uitslagenportaal")
    pv_import = s3_storage("pvs", head_error="404")

    run_ensure_bucket(default, pv_import)

    default.connection.meta.client.head_bucket.assert_called_once_with(Bucket="uitslagenportaal")
    default.connection.meta.client.create_bucket.assert_not_called()
    pv_import.connection.meta.client.create_bucket.assert_called_once_with(Bucket="pvs")


def test_skips_a_storage_without_a_bucket():
    default = s3_storage("uitslagenportaal", head_error="404")

    run_ensure_bucket(default, InMemoryStorage())

    default.connection.meta.client.create_bucket.assert_called_once_with(Bucket="uitslagenportaal")


def test_raises_when_the_bucket_cannot_be_looked_up():
    default = s3_storage("uitslagenportaal", head_error="403")

    with pytest.raises(ClientError):
        run_ensure_bucket(default, s3_storage("pvs"))

    default.connection.meta.client.create_bucket.assert_not_called()
