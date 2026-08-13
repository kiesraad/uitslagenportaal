import pytest

from election.models import ElectionCategory, ElectionConfig
from election.tests.factories import ElectionConfigFactory, TimelineEntryFactory
from mainsite.models import RegionCategory


@pytest.mark.parametrize(
    ("category", "expected_csb"),
    [
        (ElectionCategory.TK, RegionCategory.STAAT),
        (ElectionCategory.EK, RegionCategory.STAAT),
        (ElectionCategory.EP, RegionCategory.STAAT),
        (ElectionCategory.PS, RegionCategory.PROVINCIE),
        (ElectionCategory.WS, RegionCategory.WATERSCHAP),
        (ElectionCategory.GR, RegionCategory.GEMEENTE),
    ],
)
def test_election_category_knows_which_region_is_its_csb(category, expected_csb):
    """The 510d importer resolves the region that published a Totaaltelling through this."""
    assert ElectionCategory(category.value).config.csb == expected_csb


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


@pytest.mark.django_db
def test_timeline_entries_are_ordered_chronologically():
    config = ElectionConfigFactory()
    later = TimelineEntryFactory(election_config=config, date="2023-03-20T00:00:00Z")
    earlier = TimelineEntryFactory(election_config=config, date="2023-03-10T00:00:00Z")

    assert list(config.timeline_entries.all()) == [earlier, later]
