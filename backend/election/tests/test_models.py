import pytest

from election.models import ElectionConfig, TimelineEntry


@pytest.mark.django_db
def test_election_config_slug_is_generated_from_identifier():
    config = ElectionConfig.objects.create(
        identifier="Gemeenteraadsverkiezingen 2026",
        category="GR",
        date="2026-03-18T00:00:00Z",
    )

    assert config.slug == "gemeenteraadsverkiezingen"


@pytest.mark.django_db
def test_election_config_slug_is_not_overwritten_if_already_set():
    config = ElectionConfig.objects.create(
        identifier="Gemeenteraadsverkiezingen 2026",
        category="GR",
        date="2026-03-18T00:00:00Z",
        slug="custom-slug",
    )

    assert config.slug == "custom-slug"


@pytest.mark.django_db
def test_timeline_entries_are_ordered_chronologically():
    config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    later = TimelineEntry.objects.create(
        election_config=config,
        status="pending",
        title="Later entry",
        date="2023-03-20T00:00:00Z",
        body="",
    )
    earlier = TimelineEntry.objects.create(
        election_config=config,
        status="done",
        title="Earlier entry",
        date="2023-03-10T00:00:00Z",
        body="",
    )

    assert list(config.timeline_entries.all()) == [earlier, later]
