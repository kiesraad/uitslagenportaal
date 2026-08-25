from pathlib import Path

import pytest
from django.conf import settings

from election.models import Election, ElectionCategory, VoteCount
from election.tests.factories import ElectionConfigFactory
from eml_import.utils.folder_eml_importer import FolderEMLFileHandler
from mainsite.models import RegionCategory
from region.models import Region

WS_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "eml" / "ws"


@pytest.fixture
def ws_import_folder():
    import shutil

    target = settings.BASE_DIR / ".data" / "pytest_ws"
    shutil.copytree(WS_FIXTURE_DIR, target, dirs_exist_ok=True)
    yield target
    shutil.rmtree(target, ignore_errors=True)


@pytest.fixture
def ab2023_config(db):
    return ElectionConfigFactory(
        identifier="AB2023",
        category=ElectionCategory.WS.value,
        label="Waterschappen 2023",
    )


@pytest.mark.django_db
def test_import_ws_fixtures(ab2023_config, ws_import_folder):
    FolderEMLFileHandler().import_folder(ws_import_folder)

    election = Election.objects.get(election_config=ab2023_config)
    borsele = Region.objects.get(election=election, region_name="Borsele")

    assert Region.objects.filter(
        election=election,
        parent=borsele,
        region_category=RegionCategory.STEMBUREAU,
    ).exists()
    assert VoteCount.objects.filter(contest__election=election).exists()
