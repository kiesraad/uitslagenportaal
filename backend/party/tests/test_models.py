import pytest

from election.tests.factories import ElectionFactory
from party.models import Party


@pytest.mark.django_db
def test_party_slug_is_generated_from_registered_name():
    party = Party.objects.create(election=ElectionFactory(), registered_name="Café Île Partij")

    assert party.slug == "cafe_ile_partij"


@pytest.mark.django_db
def test_party_slug_is_not_overwritten_if_already_set():
    party = Party.objects.create(
        election=ElectionFactory(),
        registered_name="Café Île Partij",
        slug="custom-slug",
    )

    assert party.slug == "custom-slug"
