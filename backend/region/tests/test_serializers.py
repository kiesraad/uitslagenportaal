import pytest

from election.models import ElectionCategory
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from mainsite.models import CountingMethod, RegionCategory
from region.models import Region
from region.serializers import RegionDetailSerializer, RegionListSerializer, RegionSummarySerializer
from region.tests.factories import RegionFactory


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


def test_list_serializer_exposes_station_number():
    region = Region(
        region_category=RegionCategory.STEMBUREAU,
        region_number="0203::SB1",
        region_name="De Regenboog",
        slug="sb1-de-regenboog",
    )

    assert RegionListSerializer(region).data["station_number"] == 1


def test_list_serializer_exposes_postal_code():
    region = Region(
        region_category=RegionCategory.STEMBUREAU,
        region_number="0203::SB1",
        region_name="De Regenboog",
        postal_code="4451 AA",
        slug="sb1-de-regenboog",
    )

    assert RegionListSerializer(region).data["postal_code"] == "4451 AA"


def test_list_serializer_station_number_is_none_for_a_gemeente():
    region = Region(
        region_category=RegionCategory.GEMEENTE,
        region_number="654",
        region_name="Borsele",
        slug="654-borsele",
    )

    assert RegionListSerializer(region).data["station_number"] is None


@pytest.mark.django_db
def test_timeline_variant_prefers_own_counting_method():
    region = RegionFactory(counting_method=CountingMethod.DSO)

    assert RegionDetailSerializer().get_timeline_variant(region) == CountingMethod.DSO


@pytest.mark.django_db
def test_timeline_variant_falls_back_to_parent_counting_method():
    parent = RegionFactory(region_category=RegionCategory.WATERSCHAP, counting_method=CountingMethod.CSO)
    child = RegionFactory(election=parent.election, parent=parent, counting_method=None)

    assert RegionDetailSerializer().get_timeline_variant(child) == CountingMethod.CSO


@pytest.mark.django_db
def test_timeline_variant_defaults_when_no_counting_method_available():
    region = RegionFactory(counting_method=None)

    assert RegionDetailSerializer().get_timeline_variant(region) == "DEFAULT"


@pytest.mark.django_db
def test_list_serializer_nests_the_csb_summary():
    csb = RegionFactory(region_category=RegionCategory.WATERSCHAP, region_name="Delfland")
    gemeente = RegionFactory(election=csb.election, csb=csb)

    data = RegionListSerializer(gemeente).data

    assert data["csb"]["slug"] == csb.slug
    assert data["csb"]["region_name"] == "Delfland"
    assert "csb_name" not in data
    assert "csb_slug" not in data


@pytest.mark.django_db
def test_list_serializer_csb_is_none_without_a_csb():
    assert RegionListSerializer(RegionFactory()).data["csb"] is None


@pytest.mark.django_db
def test_detail_serializer_exposes_csb_and_hsb_fields():
    election = ElectionFactory(election_config=ElectionConfigFactory(category=ElectionCategory.TK.value))
    staat = RegionFactory(election=election, region_category=RegionCategory.STAAT)
    kieskringen = [
        RegionFactory(election=election, region_category=RegionCategory.KIESKRING, parent=staat, csb=staat)
        for _ in range(2)
    ]
    gemeente = RegionFactory(election=election, parent=kieskringen[0], csb=staat)

    data = RegionDetailSerializer(gemeente).data
    csb_data = RegionDetailSerializer(staat).data

    assert data["is_csb"] is False
    assert data["csb"]["slug"] == staat.slug
    assert data["has_hsb"] is True
    assert data["hsb"]["slug"] == kieskringen[0].slug
    assert csb_data["is_csb"] is True
    assert csb_data["hsb"] is None
    assert "polling_station_pv_archive" not in data
