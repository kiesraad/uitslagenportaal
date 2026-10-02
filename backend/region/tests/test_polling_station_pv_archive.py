import zipfile
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.test import APIRequestFactory

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory, ElectionFactory
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory
from region.views import RegionDetailView, polling_station_pv_archive

factory = APIRequestFactory()


def _station(gemeente, number, name):
    return RegionFactory(
        election=gemeente.election,
        parent=gemeente,
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


def _detail(gemeente):
    slug = gemeente.election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/{gemeente.slug}", {"level": "gsb"})
    return RegionDetailView.as_view()(request, election_config=slug, region=gemeente.slug)


@pytest.mark.django_db
def test_gemeente_detail_counts_a_polling_station_once_when_it_also_has_a_corrigendum():
    election = ElectionFactory()
    gemeente = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Lisserdam")
    first = _station(gemeente, "0203::SB1", "Gemeentehuis")
    second = _station(gemeente, "0203::SB2", "School")
    _station(gemeente, "0203::SB3", "Kerk")
    _pdf(first, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 10)
    _pdf(first, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 4)
    _pdf(second, ElectionDocument.FileType.PDF_N10_2, b"%PDF-n10-2", 7)

    archive = _detail(gemeente).data["polling_station_pv_archive"]

    assert archive["present_count"] == 2
    assert archive["total_count"] == 3
    assert archive["size"] == 21
    assert archive["url"] == f"/api/{election.election_config.slug}/regions/{gemeente.slug}/polling-station-pvs.zip"


@pytest.mark.django_db
def test_gemeente_detail_has_no_archive_until_a_polling_station_report_is_in():
    gemeente = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _station(gemeente, "0203::SB1", "Gemeentehuis")

    assert _detail(gemeente).data["polling_station_pv_archive"] is None


@pytest.mark.django_db
def test_archive_download_stores_each_form_uncompressed():
    election = ElectionFactory()
    gemeente = RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Lisserdam",
        slug="lisserdam",
    )
    station = _station(gemeente, "0203::SB1", "Gemeentehuis")
    _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)
    _pdf(station, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 9)

    slug = election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/{gemeente.slug}/polling-station-pvs.zip")
    response = polling_station_pv_archive(request, election_config=slug, region=gemeente.slug)

    assert response.status_code == 200
    assert response["Content-Disposition"] == 'attachment; filename="processen-verbaal-lisserdam.zip"'
    with zipfile.ZipFile(BytesIO(b"".join(response.streaming_content))) as archive:
        assert archive.read("0203-SB1 Gemeentehuis N10-1.pdf") == b"%PDF-n10"
        assert archive.read("0203-SB1 Gemeentehuis NA14-1.pdf") == b"%PDF-na14"
        assert archive.getinfo("0203-SB1 Gemeentehuis N10-1.pdf").compress_type == zipfile.ZIP_STORED
