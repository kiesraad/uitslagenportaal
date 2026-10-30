import zipfile
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIRequestFactory

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory, ElectionFactory
from mainsite.models import RegionCategory
from region.polling_station_pv_archive import polling_station_pv_zip_storage_key, write_polling_station_pv_zip
from region.tasks import build_polling_station_pv_zip
from region.tests.factories import RegionFactory
from region.views import RegionDetailView

factory = APIRequestFactory()


def _station(municipality, number, name):
    return RegionFactory(
        election=municipality.election,
        parent=municipality,
        region_category=RegionCategory.STEMBUREAU,
        region_name=name,
        region_number=number,
    )


def _pdf(region, file_type, body, size):
    document = CertifiedElectionDocumentFactory(
        region=region,
        file_type=file_type,
        size=size,
        storage_key=f"TK2025/{region.pk}-{file_type}.pdf",
    )
    default_storage.save(document.storage_key, ContentFile(body))
    return document


def _detail(municipality, params=None):
    slug = municipality.election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/{municipality.slug}", {"level": "gsb", **(params or {})})
    return RegionDetailView.as_view()(request, election_config=slug, region=municipality.slug)


def _zip_documents(response):
    documents = response.data["documents"]
    return [document for document in documents if document["file_type"] == ElectionDocument.FileType.PDF_SB_ZIP]


def _member_names(municipality):
    key, _ = write_polling_station_pv_zip(municipality)
    with zipfile.ZipFile(BytesIO(default_storage.open(key).read())) as archive:
        return archive.namelist()


@pytest.mark.django_db
def test_municipality_detail_counts_a_polling_station_once_when_it_also_has_a_correction():
    election = ElectionFactory()
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Lisserdam")
    first = _station(municipality, "0203::SB1", "Gemeentehuis")
    second = _station(municipality, "0203::SB2", "School")
    _station(municipality, "0203::SB3", "Kerk")
    _pdf(first, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 10)
    _pdf(first, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 4)
    _pdf(second, ElectionDocument.FileType.PDF_N10_2, b"%PDF-n10-2", 7)
    key = build_polling_station_pv_zip(municipality.pk)

    [archive] = _zip_documents(_detail(municipality))

    assert archive["metadata"] == {"total": 3, "present": 2}
    assert archive["size"] == default_storage.size(key)
    assert archive["content_type"] == "application/zip"


@pytest.mark.django_db
def test_municipality_detail_has_no_archive_until_a_polling_station_report_is_in():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _station(municipality, "0203::SB1", "Gemeentehuis")
    build_polling_station_pv_zip(municipality.pk)

    assert _zip_documents(_detail(municipality)) == []


@pytest.mark.django_db
def test_municipality_detail_has_no_archive_until_the_zip_is_written():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    station = _station(municipality, "0203::SB1", "Gemeentehuis")
    _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)

    assert _zip_documents(_detail(municipality)) == []


@pytest.mark.django_db
def test_archive_zip_stores_each_form_uncompressed_under_a_readable_name():
    election = ElectionFactory(election_config__identifier="TK2025")
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Lisserdam")
    station = _station(municipality, "0203::SB1", "Gemeentehuis")
    _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)
    _pdf(station, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 9)
    key, size = write_polling_station_pv_zip(municipality)

    assert size == default_storage.size(key)
    with zipfile.ZipFile(BytesIO(default_storage.open(key).read())) as archive:
        assert archive.read("TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf") == b"%PDF-n10"
        assert archive.read("TK2025 Lisserdam SB1 Gemeentehuis NA14-1.pdf") == b"%PDF-na14"
        assert archive.getinfo("TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf").compress_type == zipfile.ZIP_STORED


@pytest.mark.django_db
def test_archive_zip_numbers_a_second_correction_on_the_same_form():
    election = ElectionFactory(election_config__identifier="TK2025")
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Lisserdam")
    station = _station(municipality, "0203::SB1", "Gemeentehuis")
    _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)
    first = _pdf(station, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 9)
    second = CertifiedElectionDocumentFactory(
        region=station,
        file_type=ElectionDocument.FileType.PDF_NA14_1,
        size=9,
        storage_key=f"TK2025/{station.pk}-na14-again.pdf",
    )
    default_storage.save(second.storage_key, ContentFile(b"%PDF-na14-again"))

    assert first.is_current and second.is_current
    assert _member_names(municipality) == [
        "TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf",
        "TK2025 Lisserdam SB1 Gemeentehuis NA14-1.pdf",
        "TK2025 Lisserdam SB1 Gemeentehuis NA14-1 2.pdf",
    ]


@pytest.mark.django_db
def test_archive_zip_lists_polling_station_forms_in_station_then_form_order():
    election = ElectionFactory(election_config__identifier="TK2025")
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Lisserdam")
    other = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE)
    later = _station(municipality, "0203::SB2", "School")
    earlier = _station(municipality, "0203::SB1", "Gemeentehuis")
    _pdf(later, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 4)
    _pdf(later, ElectionDocument.FileType.PDF_NA14_2, b"%PDF-na14-2", 4)
    _pdf(earlier, ElectionDocument.FileType.PDF_N10_2, b"%PDF-n10-2", 7)
    _pdf(earlier, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 10)
    _pdf(municipality, ElectionDocument.FileType.PDF_NA31_2, b"%PDF-gsb", 20)
    _pdf(_station(other, "0203::SB1", "Kerk"), ElectionDocument.FileType.PDF_N10_1, b"%PDF-other", 3)

    assert _member_names(municipality) == [
        "TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf",
        "TK2025 Lisserdam SB1 Gemeentehuis N10-2.pdf",
        "TK2025 Lisserdam SB2 School NA14-1.pdf",
    ]


@pytest.mark.django_db
def test_write_polling_station_pv_zip_removes_the_object_when_no_forms_remain():
    election = ElectionFactory(election_config__identifier="TK2025")
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE)
    station = _station(municipality, "0203::SB1", "Gemeentehuis")
    document = _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)
    key, _ = write_polling_station_pv_zip(municipality)
    assert default_storage.exists(key)

    document.delete()
    assert write_polling_station_pv_zip(municipality) == (None, None)
    assert not default_storage.exists(polling_station_pv_zip_storage_key(municipality))
