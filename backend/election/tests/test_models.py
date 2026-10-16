import pytest

from election.models import ElectionCategory, ElectionConfig
from election.tests.factories import ElectionConfigFactory
from mainsite.models import RegionCategory


@pytest.mark.parametrize(
    ("category", "expected_csb"),
    [
        (ElectionCategory.TK, RegionCategory.STAAT),
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


@pytest.mark.parametrize(
    ("category", "expected_has_hsb"),
    [
        (ElectionCategory.TK, True),
        (ElectionCategory.EP, True),
        (ElectionCategory.PS, True),
        (ElectionCategory.WS, False),
        (ElectionCategory.GR, False),
    ],
)
@pytest.mark.django_db
def test_has_hsb_follows_the_election_category(category, expected_has_hsb):
    config = ElectionConfigFactory(category=category.value)

    assert config.has_hsb is expected_has_hsb
