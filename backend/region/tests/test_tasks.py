import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory
from mainsite.models import RegionCategory
from region.polling_station_pv_archive import polling_station_pv_zip_storage_key
from region.tasks import build_polling_station_pv_zip
from region.tests.factories import RegionFactory


def _station(municipality, number="0203::SB1"):
    return RegionFactory(
        election=municipality.election,
        parent=municipality,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Gemeentehuis",
        region_number=number,
    )


def _pdf(station, body, file_type=ElectionDocument.FileType.PDF_N10_1):
    document = CertifiedElectionDocumentFactory(
        region=station,
        file_type=file_type,
        size=len(body),
        storage_key=f"TK2025/{station.pk}-{file_type}.pdf",
    )
    default_storage.save(document.storage_key, ContentFile(body))
    return document


def _zip_documents(municipality):
    return ElectionDocument.objects.filter(file_type=ElectionDocument.FileType.PDF_SB_ZIP, region=municipality)


@pytest.mark.django_db
def test_build_polling_station_pv_zip_writes_the_object():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _pdf(_station(municipality), b"%PDF-n10")

    key = build_polling_station_pv_zip(municipality.pk)

    assert key == polling_station_pv_zip_storage_key(municipality)
    assert default_storage.exists(key)


@pytest.mark.django_db
def test_build_polling_station_pv_zip_records_the_zip_as_a_document():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _pdf(_station(municipality), b"%PDF-n10")

    key = build_polling_station_pv_zip(municipality.pk)

    document = _zip_documents(municipality).get()
    assert document.storage_key == key
    assert document.content_type == "application/zip"
    assert document.size == default_storage.size(key)


@pytest.mark.django_db
def test_build_polling_station_pv_zip_counts_polling_stations_with_a_pv():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    corrected = _station(municipality, "0203::SB1")
    _pdf(corrected, b"%PDF-n10")
    _pdf(corrected, b"%PDF-na14", ElectionDocument.FileType.PDF_NA14_1)
    _pdf(_station(municipality, "0203::SB2"), b"%PDF-n10")
    _station(municipality, "0203::SB3")

    build_polling_station_pv_zip(municipality.pk)

    assert _zip_documents(municipality).get().metadata == {"total": 3, "present": 2}


@pytest.mark.django_db
def test_build_polling_station_pv_zip_updates_the_document_on_a_rebuild():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _pdf(_station(municipality), b"%PDF-n10")
    build_polling_station_pv_zip(municipality.pk)
    first_size = _zip_documents(municipality).get().size

    _pdf(_station(municipality, "0203::SB2"), b"%PDF-n10-second-station")
    key = build_polling_station_pv_zip(municipality.pk)

    document = _zip_documents(municipality).get()
    assert document.size == default_storage.size(key)
    assert document.size > first_size
    assert document.metadata == {"total": 2, "present": 2}


@pytest.mark.django_db
def test_build_polling_station_pv_zip_removes_the_document_when_no_forms_remain():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    document = _pdf(_station(municipality), b"%PDF-n10")
    build_polling_station_pv_zip(municipality.pk)

    document.delete()

    assert build_polling_station_pv_zip(municipality.pk) is None
    assert not _zip_documents(municipality).exists()
    assert not default_storage.exists(polling_station_pv_zip_storage_key(municipality))


@pytest.mark.django_db
def test_build_polling_station_pv_zip_ignores_an_unknown_gemeente():
    assert build_polling_station_pv_zip(0) is None
