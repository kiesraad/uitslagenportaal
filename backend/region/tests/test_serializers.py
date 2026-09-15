import pytest

from mainsite.models import CountingMethod, RegionCategory
from region.serializers import RegionDetailSerializer
from region.tests.factories import RegionFactory


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
