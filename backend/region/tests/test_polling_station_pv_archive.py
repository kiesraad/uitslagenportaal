import datetime
import zipfile
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from election.models import ElectionDocument
from election.tests.factories import CertifiedElectionDocumentFactory, ElectionFactory
from election.utils import VISIBILITY_MONTHS
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory
from region.views import RegionDetailView, polling_station_pv_archive

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


def _download(municipality, params=None):
    slug = municipality.election.election_config.slug
    request = factory.get(f"/api/{slug}/regions/{municipality.slug}/polling-station-pvs.zip", params or {})
    return polling_station_pv_archive(request, election_config=slug, region=municipality.slug)


def _member_names(response):
    with zipfile.ZipFile(BytesIO(b"".join(response.streaming_content))) as archive:
        return archive.namelist()


@pytest.mark.django_db
def test_municipality_detail_counts_a_polling_station_once_when_it_also_has_a_corrigendum():
    election = ElectionFactory()
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE, region_name="Lisserdam")
    first = _station(municipality, "0203::SB1", "Gemeentehuis")
    second = _station(municipality, "0203::SB2", "School")
    _station(municipality, "0203::SB3", "Kerk")
    _pdf(first, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 10)
    _pdf(first, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 4)
    _pdf(second, ElectionDocument.FileType.PDF_N10_2, b"%PDF-n10-2", 7)

    archive = _detail(municipality).data["polling_station_pv_archive"]

    assert archive["present_count"] == 2
    assert archive["total_count"] == 3
    assert archive["size"] == 21
    assert archive["url"] == f"/api/{election.election_config.slug}/regions/{municipality.slug}/polling-station-pvs.zip"


@pytest.mark.django_db
def test_municipality_detail_has_no_archive_until_a_polling_station_report_is_in():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _station(municipality, "0203::SB1", "Gemeentehuis")

    assert _detail(municipality).data["polling_station_pv_archive"] is None


@pytest.mark.django_db
def test_archive_download_stores_each_form_uncompressed():
    election = ElectionFactory(election_config__identifier="TK2025")
    municipality = RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Lisserdam",
        slug="lisserdam",
    )
    station = _station(municipality, "0203::SB1", "Gemeentehuis")
    _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)
    _pdf(station, ElectionDocument.FileType.PDF_NA14_1, b"%PDF-na14", 9)

    response = _download(municipality)

    assert response.status_code == 200
    assert response["Content-Disposition"] == 'attachment; filename="processen-verbaal-lisserdam.zip"'
    with zipfile.ZipFile(BytesIO(b"".join(response.streaming_content))) as archive:
        assert archive.read("TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf") == b"%PDF-n10"
        assert archive.read("TK2025 Lisserdam SB1 Gemeentehuis NA14-1.pdf") == b"%PDF-na14"
        assert archive.getinfo("TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf").compress_type == zipfile.ZIP_STORED


@pytest.mark.django_db
def test_archive_download_is_not_found_until_a_polling_station_report_is_in():
    municipality = RegionFactory(region_category=RegionCategory.GEMEENTE)
    _station(municipality, "0203::SB1", "Gemeentehuis")

    response = _download(municipality)

    assert response.status_code == 404
    assert response.data["detail"] == "No polling-station reports."


@pytest.mark.django_db
def test_archive_download_is_not_found_when_the_slug_is_not_a_municipality():
    election = ElectionFactory()
    kieskring = RegionFactory(election=election, region_category=RegionCategory.KIESKRING, slug="amsterdam")

    response = _download(kieskring)

    assert response.status_code == 404
    assert response.data["detail"] == "Region not found for this election."


@pytest.mark.django_db
def test_archive_download_is_not_found_for_an_expired_election():
    started = timezone.now() - datetime.timedelta(days=31 * VISIBILITY_MONTHS + 1)
    election = ElectionFactory(election_config__date=started)
    municipality = RegionFactory(election=election, region_category=RegionCategory.GEMEENTE)
    station = _station(municipality, "0203::SB1", "Gemeentehuis")
    _pdf(station, ElectionDocument.FileType.PDF_N10_1, b"%PDF-n10", 8)

    response = _download(municipality)

    assert response.status_code == 404
    assert response.data["detail"] == "Region not found for this election."


@pytest.mark.django_db
def test_archive_download_lists_polling_station_forms_in_station_then_form_order():
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

    assert _member_names(_download(municipality)) == [
        "TK2025 Lisserdam SB1 Gemeentehuis N10-1.pdf",
        "TK2025 Lisserdam SB1 Gemeentehuis N10-2.pdf",
        "TK2025 Lisserdam SB2 School NA14-1.pdf",
    ]
