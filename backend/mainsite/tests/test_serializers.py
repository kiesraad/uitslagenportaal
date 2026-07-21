import pytest

from election.models import Election, ElectionConfig
from mainsite.models import RegionCategory
from mainsite.serializers import ElectionSummarySerializer, RegionSummarySerializer
from region.models import Region


@pytest.mark.django_db
def test_election_summary_serializer_matches_real_model_fields():
    election_config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    election = Election.objects.create(
        election_config=election_config,
        name="Waterschappen 2023",
        subcategory="AB",
        date="2023-03-15",
    )

    data = ElectionSummarySerializer(election).data

    assert data == {
        "id": election.id,
        "name": "Waterschappen 2023",
        "subcategory": "AB",
        "date": "2023-03-15",
    }


@pytest.mark.django_db
def test_region_summary_serializer_matches_real_model_fields():
    election_config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    election = Election.objects.create(
        election_config=election_config,
        name="Waterschappen 2023",
        subcategory="AB",
        date="2023-03-15",
    )
    region = Region.objects.create(
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
