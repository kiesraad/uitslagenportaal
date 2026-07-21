import pytest

from election.models import Contest, Election, ElectionConfig, VoteCount
from mainsite.models import CountingMethod, RegionCategory
from party.models import Party
from region.models import Region
from region.serializers import RegionDetailSerializer


@pytest.fixture
def election():
    config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    return Election.objects.create(
        election_config=config,
        name="Waterschappen 2023",
        subcategory="AB",
        date="2023-03-15",
    )


@pytest.mark.django_db
def test_effective_variant_prefers_own_counting_method(election):
    region = Region.objects.create(
        election=election,
        region_number="1",
        region_category=RegionCategory.GEMEENTE,
        region_name="Own method",
        counting_method=CountingMethod.DSO,
    )

    assert RegionDetailSerializer()._effective_variant(region) == CountingMethod.DSO


@pytest.mark.django_db
def test_effective_variant_falls_back_to_parent_counting_method(election):
    parent = Region.objects.create(
        election=election,
        region_number="1",
        region_category=RegionCategory.WATERSCHAP,
        region_name="Parent",
        counting_method=CountingMethod.CSO,
    )
    child = Region.objects.create(
        election=election,
        parent=parent,
        region_number="2",
        region_category=RegionCategory.GEMEENTE,
        region_name="Child",
        counting_method=None,
    )

    assert RegionDetailSerializer()._effective_variant(child) == CountingMethod.CSO


@pytest.mark.django_db
def test_effective_variant_defaults_when_no_counting_method_available(election):
    region = Region.objects.create(
        election=election,
        region_number="1",
        region_category=RegionCategory.GEMEENTE,
        region_name="No method",
        counting_method=None,
    )

    assert RegionDetailSerializer()._effective_variant(region) == "DEFAULT"


@pytest.mark.django_db
def test_region_detail_serializer_vote_counts_are_not_deduplicated_for_gemeente():
    """
    `get_vote_counts` documents an intent to drop duplicate 510d rows for
    GEMEENTE regions, but it is never wired up as the `vote_counts` field
    (that field is a plain `VoteCountSummarySerializer(many=True)`, so DRF
    never calls `get_vote_counts`). This test pins today's actual
    (undeduplicated) behavior; it is not asserting the intended behavior.
    """
    config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    election = Election.objects.create(
        election_config=config,
        name="Waterschappen 2023",
        subcategory="AB",
        date="2023-03-15",
    )
    contest = Contest.objects.create(election=election, identifier="contest-1")
    party = Party.objects.create(election=election, registered_name="Some Party")
    region = Region.objects.create(
        election=election,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Wassenaar",
    )
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=VoteCount.EML_TYPE_510B,
    )
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=VoteCount.EML_TYPE_510D,
    )

    data = RegionDetailSerializer(region).data

    assert len(data["vote_counts"]) == 2
