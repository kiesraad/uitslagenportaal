import logging
from pathlib import Path

import pytest
from django.core.files.storage import FileSystemStorage, default_storage

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.tests.pdf_files import PDF_BYTES, barneveld, one_page_pdf, write_pdf
from eml_import.utils.pdf_file_handler import PDFFileHandler
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_imports_a_municipal_certified_document_onto_the_gemeente(tmp_path):
    region = barneveld()
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf")

    PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    document = ElectionDocument.objects.get()
    assert document.region == region
    assert document.file_type == ElectionDocument.FileType.PDF_NA31_2
    assert document.content_type == "application/pdf"
    assert document.size == len(PDF_BYTES)
    assert default_storage.open(document.storage_key).read() == PDF_BYTES
    preview_key = Path(document.storage_key).with_suffix(".png").as_posix()
    assert default_storage.open(preview_key).read().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.django_db
def test_skips_a_filename_that_was_already_imported(tmp_path):
    barneveld()
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(FileSystemStorage(location=tmp_path))

    assert handler.run() == 1
    assert handler.run() == 0
    assert ElectionDocument.objects.count() == 1


@pytest.mark.django_db
def test_imports_a_polling_station_certified_document_by_stembureau_id(tmp_path):
    gemeente = barneveld()
    station = RegionFactory(
        election=gemeente.election,
        parent=gemeente,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Gemeentehuis",
        region_number="0203::SB1",
    )
    write_pdf(tmp_path, "TK2025_N10-1_0203::SB1.pdf")

    PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    document = ElectionDocument.objects.get()
    assert document.region == station
    assert document.file_type == ElectionDocument.FileType.PDF_N10_1


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
        write_pdf(tmp_path, name, one_page_pdf(name.encode()))

    PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    file_type = ElectionDocument.FileType
    attached = {(document.region_id, document.file_type) for document in ElectionDocument.objects.all()}
    assert attached == {
        (station.id, file_type.PDF_N10_1),
        (station.id, file_type.PDF_N10_2),
        (station.id, file_type.PDF_NA14_1),
        (gemeente.id, file_type.PDF_NA31_1),
        (gemeente.id, file_type.PDF_NA31_2),
        (gemeente.id, file_type.PDF_NA14_2),
        (kieskring.id, file_type.PDF_O7),
    }


@pytest.mark.django_db
def test_imports_p22_onto_the_csb_of_that_election(tmp_path):
    file_type = ElectionDocument.FileType
    cases = (
        (ElectionCategory.TK, "Country", file_type.PDF_P22_1),
        (ElectionCategory.PS, "Province", file_type.PDF_P22_1),
        (ElectionCategory.WS, "Board", file_type.PDF_P22_2),
        (ElectionCategory.GR, "Town", file_type.PDF_P22_2),
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
        filename = f"{category.value}_{document_type.removeprefix('PDF_')}_{region_name}.pdf"
        write_pdf(tmp_path, filename, one_page_pdf(filename.encode()))
        expected.add((csb.id, document_type))

    PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    attached = {(document.region_id, document.file_type) for document in ElectionDocument.objects.all()}
    assert attached == expected


@pytest.mark.django_db
def test_logs_a_bad_filename_and_imports_the_rest(tmp_path, caplog):
    barneveld()
    write_pdf(tmp_path, "NA31-2_Barneveld.pdf")
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf")

    with caplog.at_level(logging.ERROR):
        imported = PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    assert imported == 1
    assert ElectionDocument.objects.count() == 1
    assert "NA31-2_Barneveld.pdf" in caplog.text
