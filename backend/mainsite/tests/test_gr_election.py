"""
Import the Westerwolde GR fixtures and check what each level shows. In a gemeenteraadsverkiezing
the gemeente is its own CSB: one region carries the 510b (GSB) and the 510d (CSB).
"""

import re
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from election.models import Election, ElectionCategory, ElectionConfig, ElectionDocument, VoteCount
from eml_import.utils.folder_eml_file_handler import FolderEMLFileHandler
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.views import CSBPartyResultMatrixView
from region.models import Region
from region.views import RegionDetailView

GR_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "eml" / "gr"
TELLING = "Telling_GR2026_Westerwolde.eml.xml"

# Gemeentebelangen Westerwolde (list 1), candidates F.J. Luth (1) and M. Visscher (2).
PARTY_SLUG = "gemeentebelangen-westerwolde"
PARTY_VOTES = 1969
LUTH_VOTES = 1176
VISSCHER_VOTES = 225
SB1_LUTH_VOTES = 81
SB1_VISSCHER_VOTES = 5
STEMBUREAU_COUNT = 23

factory = APIRequestFactory()


@pytest.fixture
def gr_import_folder():
    target = settings.BASE_DIR / ".data" / "pytest_gr"
    shutil.copytree(GR_FIXTURE_DIR, target, dirs_exist_ok=True)
    yield target
    shutil.rmtree(target, ignore_errors=True)


@pytest.fixture
def gr_election(db, gr_import_folder):
    config = ElectionConfig.objects.create(
        identifier="GR2026",
        category=ElectionCategory.GR.value,
        label="Gemeenteraadsverkiezingen 2026",
        date=timezone.now() - timedelta(days=1),
    )
    FolderEMLFileHandler(gr_import_folder).run()
    return Election.objects.get(election_config=config)


@pytest.fixture
def westerwolde(gr_election):
    return Region.objects.get(election=gr_election, region_category=RegionCategory.GEMEENTE)


def _region_detail(region: Region, level: str, **extra) -> dict:
    slug = region.election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/{region.slug}", {"level": level, **extra})
    response = RegionDetailView.as_view()(request, election_config=slug, region=region.slug)
    assert response.status_code == 200, response.data
    return response.data


def _candidate_votes(payload: dict, position: int) -> int:
    return next(
        vote_count["valid_votes"]
        for vote_count in payload["vote_counts"]
        if vote_count["party"]["slug"] == PARTY_SLUG
        and vote_count["candidate"]
        and vote_count["candidate"]["position"] == position
    )


def _stembureau_1(gemeente: Region) -> Region:
    return Region.objects.get(parent=gemeente, region_number="1950::SB1")


def _write_corrected_telling(folder: Path) -> None:
    """Move 10 votes from Luth to Visscher at stembureau 1 and in the gemeente total, in a newer 510b."""
    path = folder / TELLING
    telling = path.read_text(encoding="utf-8")

    def add_votes(text: str, marker: str, position: int, votes: int) -> str:
        """Add votes to the first count of the candidate after marker."""
        pattern = re.compile(rf'<CandidateIdentifier Id="{position}"/>\s*</Candidate>\s*<ValidVotes>(\d+)<')
        match = pattern.search(text, text.index(marker))
        return text[: match.start(1)] + str(int(match[1]) + votes) + text[match.end(1) :]

    telling = telling.replace("2026-03-19T08:35:45.049", "2026-10-30T12:00:00.000+01:00")
    for marker in ("<TotalVotes>", '<ReportingUnitIdentifier Id="1950::SB1">'):
        telling = add_votes(telling, marker, 1, -10)
        telling = add_votes(telling, marker, 2, 10)
    path.write_text(telling, encoding="utf-8")


@pytest.mark.django_db
def test_the_gemeente_is_the_root_and_the_csb_of_its_stembureaus(gr_election, westerwolde):
    stembureaus = Region.objects.filter(election=gr_election, region_category=RegionCategory.STEMBUREAU)

    assert westerwolde.region_name == "Westerwolde"
    assert westerwolde.parent is None
    assert westerwolde.csb is None
    assert stembureaus.count() == STEMBUREAU_COUNT
    assert set(stembureaus.values_list("parent", "csb").distinct()) == {(westerwolde.pk, westerwolde.pk)}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("level", "eml_type", "file_types"),
    [
        ("gsb", EmlType.EML_510b, {ElectionDocument.FileType.EML_510B}),
        ("csb", EmlType.EML_510d, {ElectionDocument.FileType.EML_510D, ElectionDocument.FileType.EML_520}),
    ],
)
def test_each_level_of_the_gemeente_shows_its_own_telling(westerwolde, level, eml_type, file_types):
    payload = _region_detail(westerwolde, level)

    assert {vote_count["eml_type"] for vote_count in payload["vote_counts"]} == {eml_type}
    assert {document["file_type"] for document in payload["documents"]} == file_types
    assert _candidate_votes(payload, 1) == LUTH_VOTES
    assert _candidate_votes(payload, 2) == VISSCHER_VOTES


@pytest.mark.django_db
def test_a_stembureau_shows_its_510b_counts(westerwolde):
    payload = _region_detail(_stembureau_1(westerwolde), "sb", parent_region=westerwolde.slug)

    assert {vote_count["eml_type"] for vote_count in payload["vote_counts"]} == {EmlType.EML_510b}
    assert _candidate_votes(payload, 1) == SB1_LUTH_VOTES


@pytest.mark.django_db
def test_the_csb_party_matrix_has_only_the_gemeente_total(gr_election, westerwolde):
    request = factory.get(
        "/api/party-result-matrix/",
        {"election": gr_election.slug, "party": PARTY_SLUG, "csb": westerwolde.slug},
    )
    response = CSBPartyResultMatrixView.as_view()(request)

    assert response.status_code == 200, response.data
    assert response.data["columns"] == []
    assert response.data["totals"]["total"] == PARTY_VOTES
    assert response.data["rows"][0]["total"] == LUTH_VOTES


@pytest.mark.django_db
def test_a_corrected_telling_replaces_the_gemeente_and_stembureau_counts(gr_import_folder, westerwolde):
    _write_corrected_telling(gr_import_folder)
    FolderEMLFileHandler(gr_import_folder).run()

    gsb = _region_detail(westerwolde, "gsb")
    stembureau = _region_detail(_stembureau_1(westerwolde), "sb", parent_region=westerwolde.slug)
    assert _candidate_votes(gsb, 1) == LUTH_VOTES - 10
    assert _candidate_votes(gsb, 2) == VISSCHER_VOTES + 10
    assert _candidate_votes(stembureau, 1) == SB1_LUTH_VOTES - 10
    assert _candidate_votes(stembureau, 2) == SB1_VISSCHER_VOTES + 10
    assert Region.objects.filter(parent=westerwolde).count() == STEMBUREAU_COUNT
    assert (
        ElectionDocument.objects.filter(region=westerwolde, file_type=ElectionDocument.FileType.EML_510B).count() == 1
    )
    # The 510d is a separate file, which this correction leaves alone.
    assert (
        VoteCount.objects.get(
            region=westerwolde,
            party__slug=PARTY_SLUG,
            candidate__position=1,
            eml_type=EmlType.EML_510d,
        ).valid_votes
        == LUTH_VOTES
    )
