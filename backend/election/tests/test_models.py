import pytest

from election.models import ElectionCategory, ElectionConfig
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


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


def _csb_with_kieskringen(config, *names):
    election = ElectionFactory(election_config=config)
    csb = RegionFactory(election=election, region_category=RegionCategory.PROVINCIE)
    for name in names:
        RegionFactory(
            election=election, parent=csb, csb=csb, region_category=RegionCategory.KIESKRING, region_name=name
        )


@pytest.mark.django_db
def test_has_hsb_false_without_any_kieskring():
    assert ElectionConfigFactory().has_hsb is False


@pytest.mark.django_db
def test_has_hsb_false_when_each_csb_has_a_single_kieskring():
    """A CSB with one kieskring (a WS, or a PS province such as Drenthe) counts it itself; there is no HSB."""
    config = ElectionConfigFactory()
    _csb_with_kieskringen(config, "Assen")

    assert config.has_hsb is False


@pytest.mark.django_db
def test_has_hsb_true_when_a_csb_has_several_kieskringen_without_results():
    config = ElectionConfigFactory()
    _csb_with_kieskringen(config, "Assen")
    _csb_with_kieskringen(config, "Leiden", "Rotterdam")

    assert config.has_hsb is True
