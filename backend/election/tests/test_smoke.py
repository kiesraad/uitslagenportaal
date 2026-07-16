import pytest

from election.models import ElectionConfig


@pytest.mark.django_db
def test_election_config_slug_is_generated_from_identifier():
    config = ElectionConfig.objects.create(
        identifier="Gemeenteraadsverkiezingen 2026",
        category="GR",
        date="2026-03-18T00:00:00Z",
    )

    assert config.slug == "gemeenteraadsverkiezingen"
