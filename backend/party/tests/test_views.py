import pytest
from rest_framework.test import APIRequestFactory

from election.models import VoteCount
from election.tests.factories import ContestFactory, ElectionFactory
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.tests.factories import CandidateFactory, PartyFactory
from party.views import CSBPartyResultMatrixView, HSBPartyResultMatrixView
from region.tests.factories import RegionFactory

factory = APIRequestFactory()


def _matrix_request(election_slug, party_slug, csb_slug):
    return factory.get(
        "/api/party-result-matrix/",
        {
            "election": election_slug,
            "party": party_slug,
            "csb": csb_slug,
        },
    )


@pytest.mark.django_db
def test_party_result_matrix_requires_query_params():
    response = CSBPartyResultMatrixView.as_view()(factory.get("/api/party-result-matrix/"))

    assert response.status_code == 400


@pytest.mark.django_db
def test_party_result_matrix_returns_404_for_unknown_party():
    election = ElectionFactory()
    csb = RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP)

    response = CSBPartyResultMatrixView.as_view()(_matrix_request(election.slug, "unknown-party", csb.slug))

    assert response.status_code == 404
    assert response.data["party"] == "Party not found for this election."


@pytest.mark.django_db
def test_party_result_matrix_returns_404_for_unknown_csb():
    election = ElectionFactory()
    party = PartyFactory(election=election)

    response = CSBPartyResultMatrixView.as_view()(_matrix_request(election.slug, party.slug, "unknown-csb"))

    assert response.status_code == 404
    assert response.data["csb"] == "CSB not found for this election."


@pytest.mark.django_db
def test_party_result_matrix_selects_party_for_specific_election():
    election_config = ElectionFactory().election_config
    election_a = ElectionFactory(election_config=election_config, subcategory="WSA")
    election_b = ElectionFactory(election_config=election_config, subcategory="WSB")
    party_a = PartyFactory(election=election_a, registered_name="Same List")
    PartyFactory(election=election_b, registered_name="Same List")
    csb = RegionFactory(election=election_a, region_category=RegionCategory.WATERSCHAP)

    response = CSBPartyResultMatrixView.as_view()(_matrix_request(election_a.slug, party_a.slug, csb.slug))

    assert response.status_code == 200
    assert response.data["party"]["slug"] == party_a.slug


@pytest.mark.django_db
def test_party_result_matrix_returns_candidate_votes_per_gemeente():
    election = ElectionFactory()
    contest = ContestFactory(election=election)
    party = PartyFactory(election=election)
    csb = RegionFactory(
        election=election,
        region_category=RegionCategory.WATERSCHAP,
        region_name="Waterschap Alpha",
    )
    kieskring = RegionFactory(
        election=election,
        parent=csb,
        csb=csb,
        region_category=RegionCategory.KIESKRING,
        region_name="Kieskring Alpha",
    )
    gemeente_a = RegionFactory(
        election=election,
        parent=kieskring,
        csb=csb,
        region_category=RegionCategory.GEMEENTE,
        region_name="Bravo",
    )
    gemeente_b = RegionFactory(
        election=election,
        parent=kieskring,
        csb=csb,
        region_category=RegionCategory.GEMEENTE,
        region_name="Alpha",
    )
    candidate_one = CandidateFactory(contest=contest, party=party, position=1, last_name="Jansen")
    candidate_two = CandidateFactory(contest=contest, party=party, position=2, last_name="Bakker")

    VoteCount.objects.create(
        contest=contest,
        region=gemeente_a,
        party=party,
        candidate=candidate_one,
        valid_votes=11,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        candidate=candidate_one,
        valid_votes=22,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        candidate=candidate_two,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=csb,
        party=party,
        candidate=candidate_one,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=csb,
        party=party,
        candidate=candidate_two,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_a,
        party=party,
        valid_votes=11,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        valid_votes=55,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )
    VoteCount.objects.create(
        contest=contest,
        region=csb,
        party=party,
        valid_votes=66,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    response = CSBPartyResultMatrixView.as_view()(_matrix_request(election.slug, party.slug, csb.slug))

    assert response.status_code == 200
    assert response.data["party"] == {"registered_name": party.registered_name, "slug": party.slug}
    assert response.data["csb"] == {"region_name": csb.region_name, "slug": csb.slug}
    assert [column["region_name"] for column in response.data["columns"]] == ["Alpha", "Bravo"]
    assert [row["candidate"]["last_name"] for row in response.data["rows"]] == ["Jansen", "Bakker"]
    assert response.data["rows"][0]["total"] == 33
    assert response.data["rows"][0]["votes"][gemeente_a.slug] == 11
    assert response.data["rows"][0]["votes"][gemeente_b.slug] == 22
    assert response.data["rows"][1]["total"] == 33
    assert response.data["rows"][1]["votes"][gemeente_a.slug] is None
    assert response.data["rows"][1]["votes"][gemeente_b.slug] == 33
    assert response.data["totals"] == {
        "total": 66,
        "votes": {
            gemeente_a.slug: 11,
            gemeente_b.slug: 55,
        },
    }


def _hsb_matrix_request(election_slug, party_slug, hsb_slug):
    return factory.get(
        "/api/hsb-party-result-matrix/",
        {
            "election": election_slug,
            "party": party_slug,
            "hsb": hsb_slug,
        },
    )


@pytest.mark.django_db
def test_hsb_party_result_matrix_requires_query_params():
    response = HSBPartyResultMatrixView.as_view()(factory.get("/api/hsb-party-result-matrix/"))

    assert response.status_code == 400


@pytest.mark.django_db
def test_hsb_party_result_matrix_returns_404_for_unknown_kieskring():
    election = ElectionFactory()
    party = PartyFactory(election=election)

    response = HSBPartyResultMatrixView.as_view()(_hsb_matrix_request(election.slug, party.slug, "unknown-hsb"))

    assert response.status_code == 404
    assert response.data["hsb"] == "Kieskring not found for this election."


@pytest.mark.django_db
def test_hsb_party_result_matrix_returns_candidate_votes_per_gemeente():
    election = ElectionFactory()
    party = PartyFactory(election=election)
    provincie = RegionFactory(election=election, region_category=RegionCategory.PROVINCIE, region_name="Zuid-Holland")
    kieskring = RegionFactory(
        election=election,
        parent=provincie,
        csb=provincie,
        region_category=RegionCategory.KIESKRING,
        region_name="Leiden",
    )
    contest = ContestFactory(election=election, identifier="4", name="Leiden")
    gemeente_a = RegionFactory(
        election=election,
        parent=kieskring,
        csb=provincie,
        region_category=RegionCategory.GEMEENTE,
        region_name="Leiden",
    )
    gemeente_b = RegionFactory(
        election=election,
        parent=kieskring,
        csb=provincie,
        region_category=RegionCategory.GEMEENTE,
        region_name="Oegstgeest",
    )
    candidate_one = CandidateFactory(contest=contest, party=party, position=1, last_name="Jansen")
    candidate_two = CandidateFactory(contest=contest, party=party, position=2, last_name="Bakker")

    VoteCount.objects.create(
        contest=contest,
        region=gemeente_a,
        party=party,
        candidate=candidate_one,
        valid_votes=11,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        candidate=candidate_one,
        valid_votes=22,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        candidate=candidate_two,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        candidate=candidate_one,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        candidate=candidate_two,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_a,
        party=party,
        valid_votes=11,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        valid_votes=55,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        valid_votes=66,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510c,
    )
    # A stale 510d row from the CSB's breakdown, which the HSB's own 510c data should shadow.
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        valid_votes=999,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510d,
    )

    response = HSBPartyResultMatrixView.as_view()(_hsb_matrix_request(election.slug, party.slug, kieskring.slug))

    assert response.status_code == 200
    assert response.data["party"] == {"registered_name": party.registered_name, "slug": party.slug}
    assert response.data["hsb"] == {"region_name": kieskring.region_name, "slug": kieskring.slug}
    assert [column["region_name"] for column in response.data["columns"]] == ["Leiden", "Oegstgeest"]
    assert response.data["rows"][0]["total"] == 33
    assert response.data["rows"][0]["votes"][gemeente_a.slug] == 11
    assert response.data["rows"][0]["votes"][gemeente_b.slug] == 22
    assert response.data["totals"] == {
        "total": 66,
        "votes": {
            gemeente_a.slug: 11,
            gemeente_b.slug: 55,
        },
    }


@pytest.mark.django_db
def test_hsb_party_result_matrix_excludes_candidates_of_other_kieskringen():
    """
    A party fields a candidate at the same position in each kieskring's own contest, so the
    same name can appear as several distinct Candidate rows for one party. The matrix for one
    kieskring must only show the row that belongs to its own contest, not all of them.
    """
    election = ElectionFactory()
    party = PartyFactory(election=election)
    provincie = RegionFactory(election=election, region_category=RegionCategory.PROVINCIE, region_name="Zuid-Holland")
    leiden = RegionFactory(
        election=election,
        parent=provincie,
        csb=provincie,
        region_category=RegionCategory.KIESKRING,
        region_name="Leiden",
    )
    rotterdam = RegionFactory(
        election=election,
        parent=provincie,
        csb=provincie,
        region_category=RegionCategory.KIESKRING,
        region_name="Rotterdam",
    )
    leiden_contest = ContestFactory(election=election, identifier="4", name="Leiden")
    rotterdam_contest = ContestFactory(election=election, identifier="2", name="Rotterdam")
    leiden_candidate = CandidateFactory(contest=leiden_contest, party=party, position=1, last_name="Kegel")
    rotterdam_candidate = CandidateFactory(contest=rotterdam_contest, party=party, position=1, last_name="Kegel")

    VoteCount.objects.create(
        contest=leiden_contest,
        region=leiden,
        party=party,
        candidate=leiden_candidate,
        valid_votes=8850,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=rotterdam_contest,
        region=rotterdam,
        party=party,
        candidate=rotterdam_candidate,
        valid_votes=2935,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )

    response = HSBPartyResultMatrixView.as_view()(_hsb_matrix_request(election.slug, party.slug, leiden.slug))

    assert response.status_code == 200
    assert len(response.data["rows"]) == 1
    assert response.data["rows"][0]["candidate"]["last_name"] == "Kegel"
    assert response.data["rows"][0]["total"] == 8850


@pytest.mark.django_db
def test_hsb_party_result_matrix_supports_a_kieskring_with_a_single_gemeente():
    election = ElectionFactory()
    party = PartyFactory(election=election)
    provincie = RegionFactory(election=election, region_category=RegionCategory.PROVINCIE, region_name="Zuid-Holland")
    kieskring = RegionFactory(
        election=election,
        parent=provincie,
        csb=provincie,
        region_category=RegionCategory.KIESKRING,
        region_name="Rotterdam",
    )
    contest = ContestFactory(election=election, identifier="2", name="Rotterdam")
    gemeente = RegionFactory(
        election=election,
        parent=kieskring,
        csb=provincie,
        region_category=RegionCategory.GEMEENTE,
        region_name="Rotterdam",
    )
    candidate = CandidateFactory(contest=contest, party=party, position=1, last_name="Jansen")

    VoteCount.objects.create(
        contest=contest,
        region=gemeente,
        party=party,
        candidate=candidate,
        valid_votes=42,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )
    VoteCount.objects.create(
        contest=contest,
        region=kieskring,
        party=party,
        candidate=candidate,
        valid_votes=42,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510c,
    )

    response = HSBPartyResultMatrixView.as_view()(_hsb_matrix_request(election.slug, party.slug, kieskring.slug))

    assert response.status_code == 200
    assert [column["region_name"] for column in response.data["columns"]] == ["Rotterdam"]
    assert response.data["rows"][0]["total"] == 42
    assert response.data["rows"][0]["votes"][gemeente.slug] == 42


@pytest.mark.django_db
def test_hsb_party_result_matrix_does_not_use_510d_without_its_own_hsb():
    election = ElectionFactory()
    contest = ContestFactory(election=election)
    party = PartyFactory(election=election)
    waterschap = RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP)
    kieskring = RegionFactory(
        election=election,
        parent=waterschap,
        csb=waterschap,
        region_category=RegionCategory.KIESKRING,
        region_name=waterschap.region_name,
    )
    gemeente = RegionFactory(
        election=election,
        parent=kieskring,
        csb=waterschap,
        region_category=RegionCategory.GEMEENTE,
    )
    candidate = CandidateFactory(contest=contest, party=party, position=1, last_name="Jansen")

    VoteCount.objects.create(
        contest=contest,
        region=gemeente,
        party=party,
        candidate=candidate,
        valid_votes=17,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=EmlType.EML_510d,
    )

    response = HSBPartyResultMatrixView.as_view()(_hsb_matrix_request(election.slug, party.slug, kieskring.slug))

    assert response.status_code == 200
    assert response.data["rows"][0]["votes"][gemeente.slug] is None
    assert response.data["rows"][0]["total"] is None
