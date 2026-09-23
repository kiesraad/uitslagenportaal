import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from election.models import ElectionCategory, VoteCount, VoterTurnoutCount
from election.tests.factories import ContestFactory, ElectionFactory
from election.utils import VISIBILITY_MONTHS
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.tests.factories import PartyFactory
from region.tests.factories import RegionFactory
from region.views import RegionDetailView, RegionListView

factory = APIRequestFactory()


def list_regions(election, params):
    slug = election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/", params)
    return RegionListView.as_view()(request, election_config=slug)


def get_region(election, region_slug, params):
    slug = election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/{region_slug}", params)
    return RegionDetailView.as_view()(request, election_config=slug, region=region_slug)


@pytest.mark.django_db
def test_region_list_requires_a_filter():
    response = list_regions(ElectionFactory(), {})

    assert response.status_code == 400


@pytest.mark.django_db
def test_region_list_rejects_unknown_region_category():
    response = list_regions(ElectionFactory(), {"region_category": "NOT_A_CATEGORY"})

    assert response.status_code == 400


@pytest.mark.django_db
def test_region_list_filters_by_election_config_and_region_category():
    election = ElectionFactory()
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Bravo")
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Alpha")
    RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP)

    response = list_regions(election, {"region_category": RegionCategory.GEMEENTE})

    assert response.status_code == 200
    names = [region["region_name"] for region in response.data]
    assert names == ["Alpha", "Bravo"]


@pytest.mark.django_db
def test_region_list_filters_gemeentes_by_csb():
    election = ElectionFactory()
    waterschap_a = RegionFactory(
        election=election,
        region_category=RegionCategory.WATERSCHAP,
        region_name="Aa en Maas",
        slug="20-aa-en-maas",
    )
    waterschap_b = RegionFactory(
        election=election,
        region_category=RegionCategory.WATERSCHAP,
        region_name="Brabantse Delta",
        slug="25-brabantse-delta",
    )
    kieskring_a = RegionFactory(
        election=election,
        parent=waterschap_a,
        csb=waterschap_a,
        region_category=RegionCategory.KIESKRING,
        region_name="Kieskring A",
    )
    kieskring_b = RegionFactory(
        election=election,
        parent=waterschap_b,
        csb=waterschap_b,
        region_category=RegionCategory.KIESKRING,
        region_name="Kieskring B",
    )
    RegionFactory(
        election=election,
        parent=kieskring_a,
        csb=waterschap_a,
        region_category=RegionCategory.GEMEENTE,
        region_name="Asten",
    )
    RegionFactory(
        election=election,
        parent=kieskring_a,
        csb=waterschap_a,
        region_category=RegionCategory.GEMEENTE,
        region_name="Someren",
    )
    RegionFactory(
        election=election,
        parent=kieskring_b,
        csb=waterschap_b,
        region_category=RegionCategory.GEMEENTE,
        region_name="Breda",
    )

    response = list_regions(election, {"region_category": RegionCategory.GEMEENTE, "csb": waterschap_a.slug})

    assert response.status_code == 200
    names = [region["region_name"] for region in response.data]
    assert names == ["Asten", "Someren"]


@pytest.mark.django_db
def test_region_detail_requires_reporting_level():
    response = get_region(ElectionFactory(), "anywhere", {})

    assert response.status_code == 400
    assert "level" in response.data


@pytest.mark.django_db
def test_region_detail_returns_404_for_nonexistent_region():
    response = get_region(ElectionFactory(), "does-not-exist", {"level": "gsb"})

    assert response.status_code == 404
    assert response.data["detail"] == "Region not found for this election."


@pytest.mark.django_db
def test_csb_region_detail_returns_404_for_unknown_election_config():
    request = factory.get("/api/unknown/regions/anywhere", {"level": "csb"})

    response = RegionDetailView.as_view()(request, election_config="unknown", region="anywhere")

    assert response.status_code == 404


def region_detail(region, level):
    response = get_region(region.election, region.slug, {"level": level})
    assert response.status_code == 200
    return response.data


@pytest.mark.django_db
def test_gsb_returns_510b_and_csb_returns_510d_for_the_same_region():
    # A gemeente is only the CSB in a gemeenteraadsverkiezing.
    contest = ContestFactory(election__election_config__category=ElectionCategory.GR.value)
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

    gsb = region_detail(region, "gsb")
    csb = region_detail(region, "csb")

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

    data = region_detail(region, "gsb")

    assert data["vote_counts"] == []
    assert data["voter_turnout_counts"] == []


@pytest.mark.django_db
def test_region_detail_returns_510c_for_hsb():
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

    data = region_detail(region, "hsb")

    assert len(data["vote_counts"]) == 1
    assert data["vote_counts"][0]["eml_type"] == EmlType.EML_510c


@pytest.mark.django_db
def test_region_detail_returns_510c_turnout_for_hsb():
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

    data = region_detail(region, "hsb")

    assert len(data["voter_turnout_counts"]) == 1
    assert data["voter_turnout_counts"][0]["eml_type"] == EmlType.EML_510c


@pytest.mark.django_db
def test_region_detail_disambiguates_by_parent_region():
    election = ElectionFactory()
    municipality_a = RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Alkmaar",
        slug="alkmaar",
    )
    municipality_b = RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Bergen",
        slug="bergen",
    )
    RegionFactory(
        election=election,
        parent=municipality_a,
        region_category=RegionCategory.STEMBUREAU,
        region_name="School Alkmaar",
        region_number="SB1",
        slug="SB1-basisschool",
    )
    RegionFactory(
        election=election,
        parent=municipality_b,
        region_category=RegionCategory.STEMBUREAU,
        region_name="School Bergen",
        region_number="SB1",
        slug="SB1-basisschool",
    )

    ambiguous_response = get_region(election, "SB1-basisschool", {"level": "sb"})
    assert ambiguous_response.status_code == 400

    response = get_region(election, "SB1-basisschool", {"parent_region": "bergen", "level": "sb"})

    assert response.status_code == 200
    assert response.data["region_name"] == "School Bergen"


@pytest.mark.django_db
def test_region_detail_disambiguates_waterschap_polling_station_by_csb_and_parent_region():
    """
    Waterschap elections: Waterschap -> Kieskring -> Gemeente -> Stembureau.

    Polling station detail must resolve when disambiguated with both parent gemeente
    and CSB slug (as in /gsb/{gemeente}/csb/{waterschap}/{stembureau} URLs).
    """
    election = ElectionFactory()
    waterschap = RegionFactory(
        election=election,
        region_category=RegionCategory.WATERSCHAP,
        region_name="Aa en Maas",
        slug="20-aa-en-maas",
    )
    kieskring = RegionFactory(
        election=election,
        parent=waterschap,
        csb=waterschap,
        region_category=RegionCategory.KIESKRING,
        region_name="Kieskring Noord",
        slug="kieskring-noord",
    )
    gemeente = RegionFactory(
        election=election,
        parent=kieskring,
        csb=waterschap,
        region_category=RegionCategory.GEMEENTE,
        region_name="Asten",
        slug="743-asten",
    )
    stembureau = RegionFactory(
        election=election,
        parent=gemeente,
        csb=waterschap,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Soosgebouw DN Dissel",
        region_number="SB1",
        slug="SB1-soosgebouw-dn-dissel",
    )

    response = get_region(
        election, stembureau.slug, {"parent_region": gemeente.slug, "csb": waterschap.slug, "level": "sb"}
    )

    assert response.status_code == 200
    assert response.data["region_name"] == stembureau.region_name
    assert response.data["slug"] == stembureau.slug
    assert response.data["csb_slug"] == waterschap.slug
    assert response.data["csb_name"] == waterschap.region_name


@pytest.mark.django_db
def test_region_list_is_empty_for_an_expired_election():
    # The /<slug>/gsb page reads this endpoint, so a hidden election has to
    # yield no municipalities rather than the full list.
    started = timezone.now() - datetime.timedelta(days=31 * VISIBILITY_MONTHS + 1)
    election = ElectionFactory(election_config__identifier="GR2026", election_config__date=started)
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Amstelveen")

    response = list_regions(election, {"region_category": RegionCategory.GEMEENTE})

    assert response.status_code == 200
    assert list(response.data) == []


@pytest.mark.django_db
def test_region_list_has_own_results_excludes_kieskring_without_its_own_totaaltelling():
    """A waterschap's kieskring is a structural stand-in for the CSB, with only 510d rows."""
    election = ElectionFactory()
    with_hsb = RegionFactory(election=election, region_category=RegionCategory.KIESKRING, region_name="Amsterdam")
    without_hsb = RegionFactory(
        election=election, region_category=RegionCategory.KIESKRING, region_name="Scheldestromen"
    )
    contest = ContestFactory(election=election)
    party = PartyFactory(election=election)
    VoteCount.objects.create(
        contest=contest,
        region=with_hsb,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=without_hsb,
        party=party,
        valid_votes=100,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    response = list_regions(election, {"region_category": RegionCategory.KIESKRING, "has_own_results": "true"})

    assert response.status_code == 200
    assert [region["region_name"] for region in response.data] == ["Amsterdam"]


@pytest.mark.django_db
def test_region_list_has_own_results_requires_a_supported_region_category():
    response = list_regions(
        ElectionFactory(), {"region_category": RegionCategory.STEMBUREAU, "has_own_results": "true"}
    )

    assert response.status_code == 400
