import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from election.tests.factories import ElectionFactory
from election.utils import VISIBILITY_MONTHS
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

    request = factory.get(
        "/api/regions/",
        {
            "election_config": election.election_config.slug,
            "region_category": RegionCategory.GEMEENTE,
            "csb": waterschap_a.slug,
        },
    )
    response = RegionListView.as_view()(request)

    assert response.status_code == 200
    names = [region["region_name"] for region in response.data]
    assert names == ["Asten", "Someren"]


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

    request = factory.get(
        "/api/region/",
        {
            "election_config": election.election_config.slug,
            "region": stembureau.slug,
            "parent_region": gemeente.slug,
            "csb": waterschap.slug,
        },
    )
    response = RegionDetailView.as_view()(request)

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

    request = factory.get(
        "/api/regions/",
        {"election_config": election.election_config.slug, "region_category": RegionCategory.GEMEENTE},
    )
    response = RegionListView.as_view()(request)

    assert response.status_code == 200
    assert list(response.data) == []
