import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory
from mainsite.models import RegionCategory
from region.polling_station_pv_archive import polling_station_pv_zip_storage_key
from region.tasks import build_polling_station_pv_zip
from region.tests.factories import RegionFactory


def _station(municipality):
    return RegionFactory(
        election=municipality.election,
        parent=municipality,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Gemeentehuis",
        region_number="0203::SB1",
    )


@pytest.mark.django_db
def test_build_polling_station_pv_zip_writes_the_object():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    station = _station(municipality)
    document = CertifiedElectionDocumentFactory(
        region=station,
        file_type=ElectionDocument.FileType.PDF_N10_1,
        size=8,
        storage_key=f"TK2025/{station.pk}-n10.pdf",
    )
    default_storage.save(document.storage_key, ContentFile(b"%PDF-n10"))

    key = build_polling_station_pv_zip(municipality.pk)

    assert key == polling_station_pv_zip_storage_key(municipality)
    assert default_storage.exists(key)


@pytest.mark.django_db
def test_build_polling_station_pv_zip_ignores_an_unknown_gemeente():
    assert build_polling_station_pv_zip(0) is None
