import pytest
from rest_framework.test import APIRequestFactory

from election.models import VoteCount
from election.tests.factories import ContestFactory, ElectionFactory
from mainsite.models import RegionCategory
from party.tests.factories import CandidateFactory, PartyFactory
from party.views import PartyResultMatrixView
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
    response = PartyResultMatrixView.as_view()(factory.get("/api/party-result-matrix/"))

    assert response.status_code == 400


@pytest.mark.django_db
def test_party_result_matrix_returns_400_for_unknown_party():
    election = ElectionFactory()
    csb = RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP)

    response = PartyResultMatrixView.as_view()(
        _matrix_request(election.slug, "unknown-party", csb.slug)
    )

    assert response.status_code == 400
    assert response.data["party"] == "Party not found for this election."


@pytest.mark.django_db
def test_party_result_matrix_selects_party_for_specific_election():
    election_config = ElectionFactory().election_config
    election_a = ElectionFactory(election_config=election_config, subcategory="WSA")
    election_b = ElectionFactory(election_config=election_config, subcategory="WSB")
    party_a = PartyFactory(election=election_a, registered_name="Same List")
    PartyFactory(election=election_b, registered_name="Same List")
    csb = RegionFactory(election=election_a, region_category=RegionCategory.WATERSCHAP)

    response = PartyResultMatrixView.as_view()(
        _matrix_request(election_a.slug, party_a.slug, csb.slug)
    )

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
    intermediate = RegionFactory(election=election, parent=csb, region_category=RegionCategory.PROVINCIE)
    gemeente_a = RegionFactory(
        election=election,
        parent=intermediate,
        region_category=RegionCategory.GEMEENTE,
        region_name="Bravo",
    )
    gemeente_b = RegionFactory(
        election=election,
        parent=intermediate,
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
        eml_type="510d",
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        candidate=candidate_one,
        valid_votes=22,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type="510d",
    )
    VoteCount.objects.create(
        contest=contest,
        region=gemeente_b,
        party=party,
        candidate=candidate_two,
        valid_votes=33,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type="510d",
    )

    response = PartyResultMatrixView.as_view()(
        _matrix_request(election.slug, party.slug, csb.slug)
    )

    assert response.status_code == 200
    assert response.data["party"] == {"registered_name": party.registered_name, "slug": party.slug}
    assert response.data["csb"] == {"region_name": csb.region_name, "slug": csb.slug}
    assert [column["region_name"] for column in response.data["columns"]] == ["Alpha", "Bravo"]
    assert [row["candidate"]["last_name"] for row in response.data["rows"]] == ["Jansen", "Bakker"]
    assert response.data["rows"][0]["votes"][gemeente_a.slug] == 11
    assert response.data["rows"][0]["votes"][gemeente_b.slug] == 22
    assert response.data["rows"][1]["votes"][gemeente_a.slug] is None
    assert response.data["rows"][1]["votes"][gemeente_b.slug] == 33
