import pytest

from election.models import VoteCount, VoterTurnoutCount
from election.tests.factories import ContestFactory
from mainsite.models import CountingMethod, RegionCategory
from mainsite.utils.eml_type import EmlType, ReportingLevel
from party.tests.factories import PartyFactory
from region.serializers import RegionDetailSerializer
from region.tests.factories import RegionFactory


def serialize_detail(region, level):
    return RegionDetailSerializer(region, context={"level": level}).data


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
def test_gsb_returns_510b_and_csb_returns_510d_for_the_same_region():
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
        valid_votes=200,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    gsb = serialize_detail(region, ReportingLevel.GSB)
    csb = serialize_detail(region, ReportingLevel.CSB)

    assert len(gsb["vote_counts"]) == 1
    assert gsb["vote_counts"][0]["eml_type"] == EmlType.EML_510b
    assert gsb["vote_counts"][0]["valid_votes"] == 100
    assert len(csb["vote_counts"]) == 1
    assert csb["vote_counts"][0]["eml_type"] == EmlType.EML_510d
    assert csb["vote_counts"][0]["valid_votes"] == 200


@pytest.mark.django_db
def test_gsb_is_empty_without_a_510b_telling():
    contest = ContestFactory()
    party = PartyFactory(election=contest.election)
    region = RegionFactory(election=contest.election, region_category=RegionCategory.GEMEENTE)
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )
    VoterTurnoutCount.objects.create(
        contest=contest,
        region=region,
        category=VoterTurnoutCount.CATEGORY_TOTALS,
        reason_code="total counted",
        votes=100,
        eml_type=EmlType.EML_510d,
    )

    data = serialize_detail(region, ReportingLevel.GSB)

    assert data["vote_counts"] == []
    assert data["voter_turnout_counts"] == []


@pytest.mark.django_db
def test_region_detail_serializer_returns_510c_for_hsb():
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

    data = serialize_detail(region, ReportingLevel.HSB)

    assert len(data["vote_counts"]) == 1
    assert data["vote_counts"][0]["eml_type"] == EmlType.EML_510c


@pytest.mark.django_db
def test_region_detail_serializer_hides_510d_when_asked_as_hsb_without_510c():
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

    data = serialize_detail(region, ReportingLevel.HSB)

    assert data["vote_counts"] == []


@pytest.mark.django_db
def test_region_detail_serializer_returns_510c_turnout_for_hsb():
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

    data = serialize_detail(region, ReportingLevel.HSB)

    assert len(data["voter_turnout_counts"]) == 1
    assert data["voter_turnout_counts"][0]["eml_type"] == EmlType.EML_510c
