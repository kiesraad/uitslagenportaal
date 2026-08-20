"""
After importing the Scheldestromen WS fixtures, assert that each API surface
returns the EML type that belongs at that reporting level:

- Waterschap / CSB region detail → 510d (totaaltelling)
- Gemeente region detail → 510b only (both types are stored)
- Stembureau region detail → 510b
- Party result matrix → 510d GSB + CSB counts
"""

from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from election.models import Election, ElectionCategory, ElectionConfig, VoteCount, VoterTurnoutCount
from eml_import.utils.folder_eml_importer import FolderEMLImporter
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.models import Party
from party.views import PartyResultMatrixView
from region.models import Region
from region.views import RegionDetailView

WS_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "eml" / "ws"

factory = APIRequestFactory()

# Concrete values from Totaaltelling_AB2023_Scheldestromen (510d) for
# Partij voor Zeeland, candidate G.C.J. Minderhoud (position 1).
PARTY_SLUG = "partij-voor-zeeland"
CANDIDATE_POSITION = 1
BORSELE_CANDIDATE_VOTES_510D = 1107
CSB_CANDIDATE_VOTES_510D = 10890
BORSELE_PARTY_VOTES_510D = 1779
CSB_PARTY_VOTES_510D = 24949


@pytest.fixture
def ws_import_folder():
    import shutil

    target = settings.BASE_DIR / ".data" / "pytest_ws_eml_type_api"
    shutil.copytree(WS_FIXTURE_DIR, target, dirs_exist_ok=True)
    yield target
    shutil.rmtree(target, ignore_errors=True)


@pytest.fixture
def ab2023_config(db):
    return ElectionConfig.objects.create(
        identifier="AB2023",
        category=ElectionCategory.WS.value,
        label="Waterschappen 2023",
        date=timezone.now() - timedelta(days=1),  # so the test remains within timeframe
    )


@pytest.fixture
def ws_election(ab2023_config, ws_import_folder):
    FolderEMLImporter().import_folder(ws_import_folder)
    return Election.objects.get(election_config=ab2023_config)


def _region_detail(election_config_slug: str, region_slug: str, **extra):
    params = {"election_config": election_config_slug, "region": region_slug, **extra}
    request = factory.get("/api/region/", params)
    response = RegionDetailView.as_view()(request)
    assert response.status_code == 200, response.data
    return response.data


def _assert_only_eml_type(payload: dict, eml_type: str) -> None:
    assert payload["vote_counts"], "expected vote_counts in response"
    assert {vc["eml_type"] for vc in payload["vote_counts"]} == {eml_type}
    assert payload["voter_turnout_counts"], "expected voter_turnout_counts in response"
    assert {tc["eml_type"] for tc in payload["voter_turnout_counts"]} == {eml_type}


@pytest.mark.django_db
def test_gemeente_stores_both_eml_types_but_region_detail_returns_510b(ws_election):
    borsele = Region.objects.get(election=ws_election, region_name="Borsele")

    assert VoteCount.objects.filter(region=borsele, eml_type=EmlType.EML_510b).exists()
    assert VoteCount.objects.filter(region=borsele, eml_type=EmlType.EML_510d).exists()
    assert VoterTurnoutCount.objects.filter(region=borsele, eml_type=EmlType.EML_510b).exists()
    assert VoterTurnoutCount.objects.filter(region=borsele, eml_type=EmlType.EML_510d).exists()

    payload = _region_detail(ws_election.election_config.slug, borsele.slug)
    _assert_only_eml_type(payload, EmlType.EML_510b)
    assert len(payload["vote_counts"]) == VoteCount.objects.filter(region=borsele, eml_type=EmlType.EML_510b).count()
    assert (
        len(payload["voter_turnout_counts"])
        == VoterTurnoutCount.objects.filter(region=borsele, eml_type=EmlType.EML_510b).count()
    )


@pytest.mark.django_db
def test_waterschap_region_detail_returns_510d(ws_election):
    csb = Region.objects.get(election=ws_election, region_category=RegionCategory.WATERSCHAP)

    assert VoteCount.objects.filter(region=csb).exists()
    assert not VoteCount.objects.filter(region=csb).exclude(eml_type=EmlType.EML_510d).exists()

    payload = _region_detail(ws_election.election_config.slug, csb.slug)
    _assert_only_eml_type(payload, EmlType.EML_510d)


@pytest.mark.django_db
def test_stembureau_region_detail_returns_510b(ws_election):
    borsele = Region.objects.get(election=ws_election, region_name="Borsele")
    stembureau = Region.objects.get(
        election=ws_election,
        parent=borsele,
        region_category=RegionCategory.STEMBUREAU,
    )

    assert VoteCount.objects.filter(region=stembureau).exists()
    assert not VoteCount.objects.filter(region=stembureau).exclude(eml_type=EmlType.EML_510b).exists()

    payload = _region_detail(
        ws_election.election_config.slug,
        stembureau.slug,
        parent_region=borsele.slug,
    )
    _assert_only_eml_type(payload, EmlType.EML_510b)


@pytest.mark.django_db
def test_party_result_matrix_returns_510d_totaaltelling_cell(ws_election):
    csb = Region.objects.get(election=ws_election, region_category=RegionCategory.WATERSCHAP)
    borsele = Region.objects.get(election=ws_election, region_name="Borsele")
    party = Party.objects.get(election=ws_election, slug=PARTY_SLUG)

    request = factory.get(
        "/api/party-result-matrix/",
        {
            "election": ws_election.slug,
            "party": party.slug,
            "csb": csb.slug,
        },
    )
    response = PartyResultMatrixView.as_view()(request)

    assert response.status_code == 200
    data = response.data
    assert data["party"]["slug"] == PARTY_SLUG
    assert borsele.slug in {column["slug"] for column in data["columns"]}

    row = next(r for r in data["rows"] if r["candidate"]["position"] == CANDIDATE_POSITION)
    assert row["votes"][borsele.slug] == BORSELE_CANDIDATE_VOTES_510D
    assert row["total"] == CSB_CANDIDATE_VOTES_510D
    assert data["totals"]["votes"][borsele.slug] == BORSELE_PARTY_VOTES_510D
    assert data["totals"]["total"] == CSB_PARTY_VOTES_510D

    # Matrix numbers must match stored 510d rows, not 510b (same numbers in this
    # fixture for Borsele, but CSB totals only exist as 510d).
    assert (
        VoteCount.objects.get(
            region=borsele,
            party=party,
            candidate__position=CANDIDATE_POSITION,
            result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
            eml_type=EmlType.EML_510d,
        ).valid_votes
        == BORSELE_CANDIDATE_VOTES_510D
    )
    assert (
        VoteCount.objects.get(
            region=csb,
            party=party,
            candidate__position=CANDIDATE_POSITION,
            result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
            eml_type=EmlType.EML_510d,
        ).valid_votes
        == CSB_CANDIDATE_VOTES_510D
    )
