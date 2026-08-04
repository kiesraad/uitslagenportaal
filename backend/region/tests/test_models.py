import pytest
from django.core.exceptions import ValidationError

from election.tests.factories import ElectionFactory
from mainsite.models import RegionCategory
from mainsite.utils.utils import name_to_slug
from region.models import Region
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_region_slug_is_generated_from_number_and_name():
    region = RegionFactory(region_number="7", region_name="Café Île")

    assert region.slug == "7-cafe-ile"


@pytest.mark.django_db
def test_region_slug_replaces_colons_in_region_number():
    region = RegionFactory(region_number="0484::SB6", region_name="Nutsgebouw Zwammerdam")

    assert region.slug == "SB6-nutsgebouw-zwammerdam"


@pytest.mark.django_db
def test_region_slug_is_truncated_to_49_characters():
    name = "A Very Long Region Name That Exceeds The Slug Field Limit"
    region = RegionFactory(region_number="1", region_name=name)

    assert len(region.slug) == 49
    assert region.slug == f"1-{name_to_slug(name)}"[:49]


@pytest.mark.django_db
def test_region_clean_rejects_parent_from_different_election():
    parent = RegionFactory(region_category=RegionCategory.PROVINCIE)
    child = Region(
        election=ElectionFactory(),
        parent=parent,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Wassenaar",
    )

    with pytest.raises(ValidationError):
        child.clean()


@pytest.mark.django_db
def test_region_save_does_not_enforce_clean_for_mismatched_parent_election():
    parent = RegionFactory(region_category=RegionCategory.PROVINCIE)

    # `clean()` is never called automatically by `save()`/`.objects.create()`,
    # so a cross-election parent currently slips through silently.
    child = RegionFactory(
        election=ElectionFactory(),
        parent=parent,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Wassenaar",
    )

    assert child.parent_id == parent.id
