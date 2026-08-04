import pytest
from rest_framework.test import APIRequestFactory

from election.tests.factories import ElectionFactory
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory
from region.views import RegionDetailView, RegionListView

factory = APIRequestFactory()


@pytest.mark.django_db
def test_region_list_requires_election_config_query_param():
    request = factory.get("/api/regions/")

    response = RegionListView.as_view()(request)

    assert response.status_code == 400


@pytest.mark.django_db
def test_region_list_rejects_unknown_region_category():
    election = ElectionFactory()
    request = factory.get(
        "/api/regions/",
        {"election_config": election.election_config.slug, "region_category": "NOT_A_CATEGORY"},
    )

    response = RegionListView.as_view()(request)

    assert response.status_code == 400


@pytest.mark.django_db
def test_region_list_filters_by_election_config_and_region_category():
    election = ElectionFactory()
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Bravo")
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Alpha")
    RegionFactory(election=election, region_category=RegionCategory.WATERSCHAP)

    request = factory.get(
        "/api/regions/",
        {"election_config": election.election_config.slug, "region_category": RegionCategory.GEMEENTE},
    )

    response = RegionListView.as_view()(request)

    assert response.status_code == 200
    names = [region["region_name"] for region in response.data]
    assert names == ["Alpha", "Bravo"]


@pytest.mark.django_db
def test_region_detail_requires_query_params():
    request = factory.get("/api/region/")

    response = RegionDetailView.as_view()(request)

    assert response.status_code == 400


@pytest.mark.django_db
def test_region_detail_returns_400_for_nonexistent_region():
    election = ElectionFactory()
    request = factory.get(
        "/api/region/",
        {"election_config": election.election_config.slug, "region": "does-not-exist"},
    )

    response = RegionDetailView.as_view()(request)

    assert response.status_code == 400
    assert response.data["detail"] == "Region not found for this election."


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

    ambiguous_request = factory.get(
        "/api/region/",
        {"election_config": election.election_config.slug, "region": "SB1-basisschool"},
    )
    ambiguous_response = RegionDetailView.as_view()(ambiguous_request)
    assert ambiguous_response.status_code == 400

    request = factory.get(
        "/api/region/",
        {
            "election_config": election.election_config.slug,
            "region": "SB1-basisschool",
            "parent_region": "bergen",
        },
    )
    response = RegionDetailView.as_view()(request)

    assert response.status_code == 200
    assert response.data["region_name"] == "School Bergen"
