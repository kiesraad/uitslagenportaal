import datetime
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from election import utils
from election.utils import (
    DELETION_GRACE_DAYS,
    delete_stored_documents,
    deletion_cutoff,
    folder_prefixes,
    tz_aware_from_isoformat,
    visibility_cutoff,
)


@pytest.fixture
def frozen_now(monkeypatch):
    """Pin timezone.now() as seen by election.utils to the given moment."""

    def freeze(now):
        monkeypatch.setattr(utils.timezone, "now", lambda: now.replace(tzinfo=datetime.timezone.utc))

    return freeze


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # Same year, the day survives untouched.
        (datetime.datetime(2026, 8, 12, 10, 0), datetime.datetime(2026, 5, 12, 10, 0)),
        # Crossing the year boundary.
        (datetime.datetime(2026, 2, 15, 9, 30), datetime.datetime(2025, 11, 15, 9, 30)),
        (datetime.datetime(2026, 1, 1, 0, 0), datetime.datetime(2025, 10, 1, 0, 0)),
        # Target month is shorter than the source month, so the day clamps.
        (datetime.datetime(2026, 5, 31, 12, 0), datetime.datetime(2026, 2, 28, 12, 0)),
        # Same clamp, but the target February is in a leap year.
        (datetime.datetime(2024, 5, 31, 12, 0), datetime.datetime(2024, 2, 29, 12, 0)),
        (datetime.datetime(2026, 7, 31, 12, 0), datetime.datetime(2026, 4, 30, 12, 0)),
    ],
)
def test_visibility_cutoff_subtracts_three_calendar_months(frozen_now, now, expected):
    frozen_now(now)

    assert visibility_cutoff() == expected.replace(tzinfo=datetime.timezone.utc)


def test_deletion_cutoff_trails_visibility_cutoff_by_the_grace_period(frozen_now):
    frozen_now(datetime.datetime(2026, 8, 12, 10, 0))

    delta = visibility_cutoff() - deletion_cutoff()

    assert delta == datetime.timedelta(days=DELETION_GRACE_DAYS)


@pytest.mark.parametrize(
    ("time_zone", "value", "expected_utc"),
    [
        # Summer time: CEST, UTC+2.
        ("Europe/Amsterdam", "2026-07-01T12:00:00", datetime.datetime(2026, 7, 1, 10, 0)),
        # Winter time: CET, UTC+1.
        ("Europe/Amsterdam", "2026-01-15T12:00:00", datetime.datetime(2026, 1, 15, 11, 0)),
        ("UTC", "2026-07-01T12:00:00", datetime.datetime(2026, 7, 1, 12, 0)),
    ],
)
def test_tz_aware_from_isoformat_reads_naive_values_in_the_project_time_zone(settings, time_zone, value, expected_utc):
    settings.TIME_ZONE = time_zone

    assert tz_aware_from_isoformat(value) == expected_utc.replace(tzinfo=datetime.timezone.utc)


class FakeBucket:
    """Deletes by prefix from the in-memory storage, like an S3 bucket does."""

    def __init__(self):
        self.objects = self

    def filter(self, Prefix):
        self.prefix = Prefix
        return self

    def delete(self):
        keys = self._keys(self.prefix.rstrip("/"))
        for key in keys:
            default_storage.delete(key)
        return [{"Deleted": [{"Key": key} for key in keys]}]

    def _keys(self, folder):
        folders, files = default_storage.listdir(folder)
        return [f"{folder}/{name}" for name in files] + [
            key for name in folders for key in self._keys(f"{folder}/{name}")
        ]


def test_delete_stored_documents_removes_the_election_folder_with_its_subfolders():
    storage_keys = ["TK2025/emls/a.eml.xml", "TK2025/csvs/b.csv", "TK2025/pvs/c.pdf", "TK2025/d.pdf"]
    stored = [*storage_keys, "TK2025/pv_thumbnails/c.png", "TK2025/d.png", "GR2026/emls/e.eml.xml"]
    for key in stored:
        default_storage.save(key, ContentFile(b"x"))

    with patch.object(default_storage, "bucket", FakeBucket(), create=True):
        deleted, failed = delete_stored_documents(storage_keys, folder_prefixes(storage_keys))

    assert (deleted, failed) == (6, [])
    assert [key for key in stored if default_storage.exists(key)] == ["GR2026/emls/e.eml.xml"]
