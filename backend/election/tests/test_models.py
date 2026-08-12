import datetime

import pytest

from election.models import DELETION_GRACE_DAYS, ElectionConfig, deletion_cutoff, visibility_cutoff
from election.tests.factories import ElectionConfigFactory, TimelineEntryFactory


@pytest.mark.django_db
def test_election_config_slug_is_generated_from_identifier():
    config = ElectionConfigFactory(identifier="Gemeenteraadsverkiezingen 2026")

    assert config.slug == "gemeenteraadsverkiezingen-2026"


@pytest.mark.django_db
def test_election_config_slug_is_not_overwritten_if_already_set():
    config = ElectionConfig.objects.create(
        identifier="Gemeenteraadsverkiezingen 2026",
        category="GR",
        date="2026-03-18T00:00:00Z",
        slug="custom-slug",
    )

    assert config.slug == "custom-slug"


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
def test_visibility_cutoff_subtracts_three_calendar_months(now, expected):
    tz = datetime.timezone.utc

    assert visibility_cutoff(now.replace(tzinfo=tz)) == expected.replace(tzinfo=tz)


def test_deletion_cutoff_trails_visibility_cutoff_by_the_grace_period():
    now = datetime.datetime(2026, 8, 12, 10, 0, tzinfo=datetime.timezone.utc)

    delta = visibility_cutoff(now) - deletion_cutoff(now)

    assert delta == datetime.timedelta(days=DELETION_GRACE_DAYS)


@pytest.mark.django_db
def test_timeline_entries_are_ordered_chronologically():
    config = ElectionConfigFactory()
    later = TimelineEntryFactory(election_config=config, date="2023-03-20T00:00:00Z")
    earlier = TimelineEntryFactory(election_config=config, date="2023-03-10T00:00:00Z")

    assert list(config.timeline_entries.all()) == [earlier, later]
