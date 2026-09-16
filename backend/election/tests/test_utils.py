import datetime

import pytest

from election import utils
from election.utils import DELETION_GRACE_DAYS, deletion_cutoff, visibility_cutoff


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
