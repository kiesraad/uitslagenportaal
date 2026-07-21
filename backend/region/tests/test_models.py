import pytest
from django.core.exceptions import ValidationError

from election.models import Election, ElectionConfig
from mainsite.models import RegionCategory
from mainsite.utils.utils import name_to_slug
from region.models import Region


@pytest.fixture
def election():
    config = ElectionConfig.objects.create(
        identifier="AB2023",
        category="AB",
        date="2023-03-15T00:00:00Z",
    )
    return Election.objects.create(
        election_config=config,
        name="Waterschappen 2023",
        subcategory="AB",
        date="2023-03-15",
    )


@pytest.mark.django_db
def test_region_slug_is_generated_from_number_and_name(election):
    region = Region.objects.create(
        election=election,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Café Île",
    )

    assert region.slug == "7-cafe_ile"


@pytest.mark.django_db
def test_region_slug_is_truncated_to_49_characters(election):
    name = "A Very Long Region Name That Exceeds The Slug Field Limit"
    region = Region.objects.create(
        election=election,
        region_number="1",
        region_category=RegionCategory.GEMEENTE,
        region_name=name,
    )

    assert len(region.slug) == 49
    assert region.slug == f"1-{name_to_slug(name)}"[:49]


@pytest.mark.django_db
def test_region_clean_rejects_parent_from_different_election(election):
    other_config = ElectionConfig.objects.create(
        identifier="TK2025",
        category="TK",
        date="2025-01-01T00:00:00Z",
    )
    other_election = Election.objects.create(
        election_config=other_config,
        name="Tweede Kamer 2025",
        subcategory="TK",
        date="2025-01-01",
    )
    parent = Region.objects.create(
        election=other_election,
        region_number="1",
        region_category=RegionCategory.PROVINCIE,
        region_name="Zuid-Holland",
    )
    child = Region(
        election=election,
        parent=parent,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Wassenaar",
    )

    with pytest.raises(ValidationError):
        child.clean()


@pytest.mark.django_db
def test_region_save_does_not_enforce_clean_for_mismatched_parent_election(election):
    other_config = ElectionConfig.objects.create(
        identifier="TK2025",
        category="TK",
        date="2025-01-01T00:00:00Z",
    )
    other_election = Election.objects.create(
        election_config=other_config,
        name="Tweede Kamer 2025",
        subcategory="TK",
        date="2025-01-01",
    )
    parent = Region.objects.create(
        election=other_election,
        region_number="1",
        region_category=RegionCategory.PROVINCIE,
        region_name="Zuid-Holland",
    )

    # `clean()` is never called automatically by `save()`/`.objects.create()`,
    # so a cross-election parent currently slips through silently.
    child = Region.objects.create(
        election=election,
        parent=parent,
        region_number="7",
        region_category=RegionCategory.GEMEENTE,
        region_name="Wassenaar",
    )

    assert child.parent_id == parent.id
