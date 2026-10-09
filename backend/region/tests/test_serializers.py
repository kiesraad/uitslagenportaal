import pytest

from mainsite.models import CountingMethod, RegionCategory
from region.models import Region
from region.serializers import RegionDetailSerializer, RegionListSerializer
from region.tests.factories import RegionFactory


def test_list_serializer_exposes_station_number():
    region = Region(
        region_category=RegionCategory.STEMBUREAU,
        region_number="0203::SB1",
        region_name="De Regenboog",
        slug="sb1-de-regenboog",
    )

    assert RegionListSerializer(region).data["station_number"] == 1


def test_list_serializer_station_number_is_none_for_a_gemeente():
    region = Region(
        region_category=RegionCategory.GEMEENTE,
        region_number="654",
        region_name="Borsele",
        slug="654-borsele",
    )

    assert RegionListSerializer(region).data["station_number"] is None


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
