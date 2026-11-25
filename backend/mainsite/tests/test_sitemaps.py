import datetime

import pytest
from django.utils import timezone

from election.tests.factories import ElectionConfigFactory


@pytest.mark.django_db
def test_index_links_to_the_sections(client):
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert b"/sitemap/verkiezingen.xml" in response.content


@pytest.mark.django_db
def test_lists_the_election_pages_without_expired_elections(client):
    ElectionConfigFactory(slug="gr2026", category="GR")
    ElectionConfigFactory(slug="ps2027", category="PS")
    ElectionConfigFactory(slug="gr2000", date=timezone.now() - datetime.timedelta(days=3650))

    content = client.get("/sitemap/verkiezingen.xml").content.decode()

    assert "https://testserver/</loc>" in content
    assert "https://testserver/gr2026/van-stem-tot-uitslag</loc>" in content
    assert "https://testserver/gr2026/gsb</loc>" in content
    assert "https://testserver/ps2027/csb</loc>" in content
    assert "gr2000" not in content
