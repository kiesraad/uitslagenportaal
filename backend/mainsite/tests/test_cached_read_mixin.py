import pytest

from election.tests.factories import ElectionConfigFactory


@pytest.mark.django_db
def test_list_is_served_from_cache_until_it_expires(client):
    ElectionConfigFactory()
    first = client.get("/api/election_configs/").json()

    ElectionConfigFactory()

    assert client.get("/api/election_configs/").json() == first


@pytest.mark.django_db
def test_cache_is_per_url(client):
    config = ElectionConfigFactory()
    client.get("/api/election_configs/")

    response = client.get(f"/api/election_configs/{config.slug}/")

    assert response.json()["slug"] == config.slug


@pytest.mark.django_db
def test_error_responses_are_not_cached(client):
    assert client.get("/api/election_configs/later/").status_code == 404

    ElectionConfigFactory(slug="later")

    assert client.get("/api/election_configs/later/").status_code == 200
