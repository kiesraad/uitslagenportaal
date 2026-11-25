import datetime

import pytest
from django.utils import timezone

from election.models import VoteCount
from election.tests.factories import ContestFactory, ElectionConfigFactory, ElectionFactory
from mainsite.models import RegionCategory
from party.tests.factories import PartyFactory
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_index_links_to_the_sections(client):
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert b"/sitemap/verkiezingen.xml" in response.content
    assert b"/sitemap/regios.xml" in response.content
    assert b"/sitemap/partijen.xml" in response.content


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


@pytest.mark.django_db
def test_lists_the_region_pages_with_their_results(client):
    election = ElectionFactory(election_config=ElectionConfigFactory(slug="ps2027", category="PS"))
    province = RegionFactory(election=election, region_category=RegionCategory.PROVINCIE, slug="utrecht")
    RegionFactory(election=election, region_category=RegionCategory.KIESKRING, parent=province, slug="kk1")
    RegionFactory(election=election, region_category=RegionCategory.KIESKRING, parent=province, slug="kk2")
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, csb=province, slug="zeist")

    content = client.get("/sitemap/regios.xml").content.decode()

    assert "https://testserver/ps2027/csb/utrecht</loc>" in content
    assert "https://testserver/ps2027/csb/utrecht/resultaten</loc>" in content
    assert "https://testserver/ps2027/hsb/kk1/resultaten</loc>" in content
    assert "https://testserver/ps2027/gsb/zeist/csb/utrecht</loc>" in content
    assert "https://testserver/ps2027/gsb/zeist/csb/utrecht/resultaten</loc>" in content


@pytest.mark.django_db
def test_leaves_out_the_csb_of_a_municipality_that_is_its_own_csb(client):
    election = ElectionFactory(election_config=ElectionConfigFactory(slug="gr2026", category="GR"))
    RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, slug="zeist")

    content = client.get("/sitemap/regios.xml").content.decode()

    assert "https://testserver/gr2026/csb/zeist</loc>" in content
    assert "https://testserver/gr2026/gsb/zeist</loc>" in content
    assert "https://testserver/gr2026/gsb/zeist/resultaten</loc>" in content


@pytest.mark.django_db
def test_lists_the_results_of_each_party_with_votes_in_the_region_or_below_it(client):
    election = ElectionFactory(election_config=ElectionConfigFactory(slug="ps2027", category="PS"))
    contest = ContestFactory(election=election)
    province = RegionFactory(election=election, region_category=RegionCategory.PROVINCIE, slug="utrecht")
    zeist = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, csb=province, slug="zeist")
    party = PartyFactory(election=election, slug="partij-a")
    PartyFactory(election=election, slug="no-votes")
    VoteCount.objects.create(contest=contest, region=zeist, party=party, valid_votes=1)

    content = client.get("/sitemap/partijen.xml").content.decode()

    assert "https://testserver/ps2027/csb/utrecht/resultaten/partij-a</loc>" in content
    assert "https://testserver/ps2027/gsb/zeist/csb/utrecht/resultaten/partij-a</loc>" in content
    assert "no-votes" not in content
