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
def test_imports_sb_gsb_and_hsb_documents_onto_those_bodies(tmp_path):
    config = ElectionConfigFactory(identifier="GEN", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    kieskring = RegionFactory(
        election=election,
        region_category=RegionCategory.KIESKRING,
        region_name="North",
        region_number="1",
    )
    gemeente = RegionFactory(
        election=election,
        parent=kieskring,
        region_category=RegionCategory.GEMEENTE,
        region_name="Alpha",
        region_number="0001",
    )
    station = RegionFactory(
        election=election,
        parent=gemeente,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Desk",
        region_number="0001::SB1",
    )
    for name in (
        "GEN_N10-1_0001::SB1.pdf",
        "GEN_N10-2_0001::SB1.pdf",
        "GEN_NA14-1_0001::SB1.pdf",
        "GEN_NA31-1_Alpha.pdf",
        "GEN_NA31-2_Alpha.pdf",
        "GEN_NA14-2_Alpha.pdf",
        "GEN_O7_North.pdf",
    ):
        write_pdf(tmp_path, name)

    FolderPDFFileHanlder(tmp_path).run()

    file_type = CertifiedElectionDocument.FileType
    attached = {(document.region_id, document.file_type) for document in CertifiedElectionDocument.objects.all()}
    assert attached == {
        (station.id, file_type.N10_1),
        (station.id, file_type.N10_2),
        (station.id, file_type.NA14_1),
        (gemeente.id, file_type.NA31_1),
        (gemeente.id, file_type.NA31_2),
        (gemeente.id, file_type.NA14_2),
        (kieskring.id, file_type.O7),
    }


@pytest.mark.django_db
def test_imports_p22_onto_the_csb_of_that_election(tmp_path):
    file_type = CertifiedElectionDocument.FileType
    cases = (
        (ElectionCategory.TK, "Country", file_type.P22_1),
        (ElectionCategory.PS, "Province", file_type.P22_1),
        (ElectionCategory.WS, "Board", file_type.P22_2),
        (ElectionCategory.GR, "Town", file_type.P22_2),
    )
    expected = set()
    for category, region_name, document_type in cases:
        config = ElectionConfigFactory(identifier=category.value, category=category.value)
        election = ElectionFactory(election_config=config, subcategory=category.value)
        csb = RegionFactory(
            election=election,
            region_category=category.config.csb,
            region_name=region_name,
            region_number="1",
        )
        write_pdf(tmp_path, f"{category.value}_{document_type}_{region_name}.pdf")
        expected.add((csb.id, document_type))

    FolderPDFFileHanlder(tmp_path).run()

    attached = {(document.region_id, document.file_type) for document in CertifiedElectionDocument.objects.all()}
    assert attached == expected


@pytest.mark.django_db
def test_rejects_a_filename_that_does_not_match_the_convention(tmp_path):
    write_pdf(tmp_path, "NA31-2_Barneveld.pdf")

    with pytest.raises(PDFImporterException, match="does not match"):
        FolderPDFFileHanlder(tmp_path).run()

    assert CertifiedElectionDocument.objects.count() == 0
