import pytest

from election.models import ElectionCategory, ElectionConfig, VoteCount
from election.tests.factories import ContestFactory, ElectionConfigFactory, ElectionFactory, TimelineEntryFactory
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.tests.factories import PartyFactory
from region.tests.factories import RegionFactory


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


@pytest.mark.django_db
def test_has_hsb_false_without_any_kieskring():
    config = ElectionConfigFactory()

    assert ElectionConfig.objects.get(pk=config.pk).has_hsb is False


@pytest.mark.django_db
def test_has_hsb_false_for_kieskring_without_its_own_totaaltelling():
    """A waterschap's kieskring is a structural stand-in for the CSB, with only 510d rows."""
    config = ElectionConfigFactory()
    election = ElectionFactory(election_config=config)
    kieskring = RegionFactory(election=election, region_category=RegionCategory.KIESKRING)
    contest = ContestFactory(election=election)
    party = PartyFactory(election=election)
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    assert ElectionConfig.objects.get(pk=config.pk).has_hsb is False


@pytest.mark.django_db
def test_has_hsb_true_for_kieskring_with_its_own_totaaltelling():
    config = ElectionConfigFactory()
    election = ElectionFactory(election_config=config)
    kieskring = RegionFactory(election=election, region_category=RegionCategory.KIESKRING)
    contest = ContestFactory(election=election)
    party = PartyFactory(election=election)
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510c,
    )

    assert ElectionConfig.objects.get(pk=config.pk).has_hsb is True
