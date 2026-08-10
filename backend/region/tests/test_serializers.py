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
def test_region_detail_serializer_filters_510d_vote_counts_for_gemeente():
    """
    Gemeente regions store both 510b (telling) and 510d (totaaltelling) rows;
    region detail only returns the 510b telling.
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
    assert data["vote_counts"][0]["eml_type"] == VoteCount.EML_TYPE_510B
