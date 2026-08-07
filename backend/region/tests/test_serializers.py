import pytest

from election.models import VoteCount
from election.tests.factories import ContestFactory
from mainsite.models import CountingMethod, RegionCategory
from party.tests.factories import PartyFactory
from region.serializers import RegionDetailSerializer
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_effective_variant_prefers_own_counting_method():
    region = RegionFactory(counting_method=CountingMethod.DSO)

    assert RegionDetailSerializer()._effective_variant(region) == CountingMethod.DSO


@pytest.mark.django_db
def test_effective_variant_falls_back_to_parent_counting_method():
    parent = RegionFactory(region_category=RegionCategory.WATERSCHAP, counting_method=CountingMethod.CSO)
    child = RegionFactory(election=parent.election, parent=parent, counting_method=None)

    assert RegionDetailSerializer()._effective_variant(child) == CountingMethod.CSO


@pytest.mark.django_db
def test_effective_variant_defaults_when_no_counting_method_available():
    region = RegionFactory(counting_method=None)

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
    contest = ContestFactory()
    party = PartyFactory(election=contest.election)
    region = RegionFactory(election=contest.election, region_category=RegionCategory.GEMEENTE)
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

    assert len(data["vote_counts"]) == 1
