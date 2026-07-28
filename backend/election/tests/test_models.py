import pytest

from election.models import ElectionConfig
from election.tests.factories import ElectionConfigFactory, TimelineEntryFactory


@pytest.mark.django_db
def test_election_config_slug_is_generated_from_identifier():
    config = ElectionConfigFactory(identifier="Gemeenteraadsverkiezingen 2026")

    assert config.slug == "gemeenteraadsverkiezingen_2026"


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
    config = ElectionConfigFactory()
    later = TimelineEntryFactory(election_config=config, date="2023-03-20T00:00:00Z")
    earlier = TimelineEntryFactory(election_config=config, date="2023-03-10T00:00:00Z")

    assert list(config.timeline_entries.all()) == [earlier, later]
