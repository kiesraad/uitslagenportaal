from pathlib import Path

import pytest
from django.core.files.storage import default_storage
from django.db import IntegrityError

from election.models import CertifiedElectionDocument, ElectionCategory
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.exceptions import PDFImporterException
from eml_import.utils.folder_pdf_file_handler import FolderPDFFileHanlder
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


def one_page_pdf(mark: bytes = b"a") -> bytes:
    """A one-page PDF pdfium can open. `mark` only changes the bytes."""
    return (
        b"%PDF-1.4\n%"
        + mark
        + b"\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        + b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        + b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        + b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )


PDF_BYTES = one_page_pdf()


def write_pdf(folder: Path, name: str, content: bytes = PDF_BYTES) -> Path:
    path = folder / name
    path.write_bytes(content)
    return path


@pytest.mark.django_db
def test_imports_a_municipal_certified_document_onto_the_gemeente(tmp_path):
    config = ElectionConfigFactory(identifier="TK2025", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    barneveld = RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Barneveld",
        region_number="203",
    )
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf")

    FolderPDFFileHanlder(tmp_path).run()

    document = CertifiedElectionDocument.objects.get()
    assert document.region == barneveld
    assert document.file_type == CertifiedElectionDocument.FileType.NA31_2
    assert document.content_type == "application/pdf"
    assert document.size == len(PDF_BYTES)
    assert default_storage.open(document.storage_key).read() == PDF_BYTES
    preview_key = Path(document.storage_key).with_suffix(".png").as_posix()
    assert default_storage.open(preview_key).read().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.django_db
def test_rejects_a_second_certified_document_for_the_same_region_and_type(tmp_path):
    config = ElectionConfigFactory(identifier="TK2025", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Barneveld",
        region_number="203",
    )
    first = one_page_pdf(b"first")
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf", first)
    FolderPDFFileHanlder(tmp_path).run()
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf", one_page_pdf(b"replaced"))

    with pytest.raises(IntegrityError):
        FolderPDFFileHanlder(tmp_path).run()

    document = CertifiedElectionDocument.objects.get()
    assert document.size == len(first)
    assert default_storage.open(document.storage_key).read() == first


@pytest.mark.django_db
def test_imports_a_polling_station_certified_document_by_stembureau_id(tmp_path):
    config = ElectionConfigFactory(identifier="TK2025", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    gemeente = RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Barneveld",
        region_number="203",
    )
    station = RegionFactory(
        election=election,
        parent=gemeente,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Gemeentehuis",
        region_number="0203::SB1",
    )
    write_pdf(tmp_path, "TK2025_N10-1_0203::SB1.pdf")

    FolderPDFFileHanlder(tmp_path).run()

    document = CertifiedElectionDocument.objects.get()
    assert document.region == station
    assert document.file_type == CertifiedElectionDocument.FileType.N10_1


@pytest.mark.django_db
def test_rejects_a_filename_that_does_not_match_the_convention(tmp_path):
    write_pdf(tmp_path, "NA31-2_Barneveld.pdf")

    with pytest.raises(PDFImporterException, match="does not match"):
        FolderPDFFileHanlder(tmp_path).run()

    assert CertifiedElectionDocument.objects.count() == 0
