import pytest

from election.tests.factories import ElectionFactory
from mainsite.models import RegionCategory
from mainsite.serializers import ElectionSummarySerializer, RegionSummarySerializer
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_election_summary_serializer_matches_real_model_fields():
    election = ElectionFactory(name="Waterschappen 2023", subcategory="AB", date="2023-03-15")

    data = ElectionSummarySerializer(election).data

    assert data == {
        "id": election.id,
        "name": "Waterschappen 2023",
        "subcategory": "AB",
        "date": "2023-03-15",
    }


@pytest.mark.django_db
def test_region_summary_serializer_matches_real_model_fields():
    election = ElectionFactory()
    region = RegionFactory(
        election=election,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Wassenaar",
    )

    data = RegionSummarySerializer(region).data

    assert data == {
        "id": region.id,
        "election_id": election.id,
        "parent_id": None,
        "region_number": "7",
        "region_category": RegionCategory.GEMEENTE,
        "region_name": "Wassenaar",
        "slug": region.slug,
    }
