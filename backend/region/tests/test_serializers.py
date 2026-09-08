import pytest

from election.models import VoteCount, VoterTurnoutCount
from election.tests.factories import ContestFactory
from mainsite.models import CountingMethod, RegionCategory
from mainsite.utils.eml_type import EmlType
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
        eml_type=EmlType.EML_510b,
    )
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    data = RegionDetailSerializer(region).data

    assert len(data["vote_counts"]) == 1
    assert data["vote_counts"][0]["eml_type"] == EmlType.EML_510b


@pytest.mark.django_db
def test_region_detail_serializer_prefers_510c_vote_counts_for_kieskring():
    """
    A kieskring with its own HSB stores both 510c (its own totaaltelling) and 510d (the CSB's
    breakdown for it); region detail prefers the 510c totaaltelling.
    """
    contest = ContestFactory()
    party = PartyFactory(election=contest.election)
    region = RegionFactory(election=contest.election, region_category=RegionCategory.KIESKRING)
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    data = RegionDetailSerializer(region).data

    assert len(data["vote_counts"]) == 1
    assert data["vote_counts"][0]["eml_type"] == EmlType.EML_510c


@pytest.mark.django_db
def test_region_detail_serializer_falls_back_to_510d_vote_counts_for_kieskring_without_hsb():
    """
    A kieskring that submitted centrally to the CSB (no HSB of its own) has only 510d rows;
    region detail falls back to those instead of returning nothing.
    """
    contest = ContestFactory()
    party = PartyFactory(election=contest.election)
    region = RegionFactory(election=contest.election, region_category=RegionCategory.KIESKRING)
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    data = RegionDetailSerializer(region).data

    assert len(data["vote_counts"]) == 1
    assert data["vote_counts"][0]["eml_type"] == EmlType.EML_510d


@pytest.mark.django_db
def test_region_detail_serializer_prefers_510c_turnout_counts_for_kieskring():
    contest = ContestFactory()
    region = RegionFactory(election=contest.election, region_category=RegionCategory.KIESKRING)
    VoterTurnoutCount.objects.create(
        contest=contest,
        region=region,
        category=VoterTurnoutCount.CATEGORY_TOTALS,
        reason_code="total counted",
        votes=100,
        eml_type=EmlType.EML_510c,
    )
    VoterTurnoutCount.objects.create(
        contest=contest,
        region=region,
        category=VoterTurnoutCount.CATEGORY_TOTALS,
        reason_code="total counted",
        votes=100,
        eml_type=EmlType.EML_510d,
    )

    data = RegionDetailSerializer(region).data

    assert len(data["voter_turnout_counts"]) == 1
    assert data["voter_turnout_counts"][0]["eml_type"] == EmlType.EML_510c
