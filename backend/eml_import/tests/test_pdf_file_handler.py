import hashlib
import logging
from pathlib import Path

import pytest
from django.core.files.storage import FileSystemStorage, default_storage

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.models import ImportedFileHash
from eml_import.tests.pdf_files import PDF_BYTES, barneveld, one_page_pdf, write_pdf
from eml_import.utils.pdf_file_handler import PDFFileHandler
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


@pytest.mark.django_db
def test_imports_a_municipal_certified_document_onto_the_gemeente(tmp_path):
    region = barneveld()
    write_pdf(tmp_path, "TK2025_Nederland_NA31-2_Barneveld.pdf")

    handler = PDFFileHandler(FileSystemStorage(location=tmp_path))
    handler.run()

    document = ElectionDocument.objects.get()
    assert handler.archive_gemeente_ids == set()
    assert document.region == region
    assert document.file_type == ElectionDocument.FileType.PDF_NA31_2
    assert document.content_type == "application/pdf"
    assert document.size == len(PDF_BYTES)
    assert default_storage.open(document.storage_key).read() == PDF_BYTES
    preview_key = Path(document.storage_key).with_suffix(".png").as_posix()
    assert default_storage.open(preview_key).read().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.django_db
def test_records_the_hash_and_skips_bytes_that_were_already_imported(tmp_path):
    region = barneveld()
    write_pdf(tmp_path, "TK2025_Nederland_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(FileSystemStorage(location=tmp_path))

    assert handler.run() == 1
    recorded = ImportedFileHash.objects.get()
    assert recorded.election == region.election
    assert recorded.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()

    assert handler.run() == 0
    assert ElectionDocument.objects.count() == 1


@pytest.mark.django_db
def test_a_rescanned_proces_verbaal_supersedes_the_one_it_replaces(tmp_path):
    region = barneveld()
    storage = FileSystemStorage(location=tmp_path)
    write_pdf(tmp_path, "TK2025_Nederland_NA31-2_Barneveld.pdf", one_page_pdf(b"first scan"))
    PDFFileHandler(storage).run()
    superseded = ElectionDocument.objects.get()

    write_pdf(tmp_path, "TK2025_Nederland_NA31-2_Barneveld.pdf", one_page_pdf(b"second scan"))
    assert PDFFileHandler(storage).run() == 1

    current = ElectionDocument.objects.get(region=region)
    assert current.pk != superseded.pk
    assert default_storage.open(current.storage_key).read() == one_page_pdf(b"second scan")
    superseded.refresh_from_db()
    assert superseded.is_current is False


@pytest.mark.django_db
def test_every_correction_on_one_form_stays_current(tmp_path):
    region = barneveld()
    storage = FileSystemStorage(location=tmp_path)
    write_pdf(tmp_path, "TK2025_Nederland_NA14-2_Barneveld.pdf", one_page_pdf(b"first correction"))
    PDFFileHandler(storage).run()

    write_pdf(tmp_path, "TK2025_Nederland_NA14-2_Barneveld.pdf", one_page_pdf(b"second correction"))
    assert PDFFileHandler(storage).run() == 1

    corrections = ElectionDocument.objects.filter(region=region).order_by("created_at", "pk")
    assert [default_storage.open(document.storage_key).read() for document in corrections] == [
        one_page_pdf(b"first correction"),
        one_page_pdf(b"second correction"),
    ]
    # Shared region and file type, so the download names have to part on their timestamp
    assert len({document.download_filename for document in corrections}) == 2


@pytest.mark.django_db
def test_imports_a_polling_station_certified_document_by_stembureau_id(tmp_path):
    gemeente = barneveld()
    station = RegionFactory(
        election=gemeente.election,
        parent=gemeente,
        csb=gemeente.csb,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Gemeentehuis",
        region_number="0203::SB1",
    )
    write_pdf(tmp_path, "TK2025_Nederland_N10-1_0203::SB1.pdf")

    handler = PDFFileHandler(FileSystemStorage(location=tmp_path))
    handler.run()

    document = ElectionDocument.objects.get()
    assert document.region == station
    assert document.file_type == ElectionDocument.FileType.PDF_N10_1
    assert handler.archive_gemeente_ids == {gemeente.id}


@pytest.mark.django_db
def test_imports_sb_gsb_and_hsb_documents_onto_those_bodies(tmp_path):
    config = ElectionConfigFactory(identifier="GEN", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    staat = RegionFactory(
        election=election,
        region_category=RegionCategory.STAAT,
        region_name="Nederland",
        region_number=None,
    )
    kieskring = RegionFactory(
        election=election,
        parent=staat,
        csb=staat,
        region_category=RegionCategory.KIESKRING,
        region_name="North",
        region_number="1",
    )
    gemeente = RegionFactory(
        election=election,
        parent=kieskring,
        csb=staat,
        region_category=RegionCategory.GEMEENTE,
        region_name="Alpha",
        region_number="0001",
    )
    station = RegionFactory(
        election=election,
        parent=gemeente,
        csb=staat,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Desk",
        region_number="0001::SB1",
    )
    for name in (
        "GEN_Nederland_N10-1_0001::SB1.pdf",
        "GEN_Nederland_N10-2_0001::SB1.pdf",
        "GEN_Nederland_NA14-1_0001::SB1.pdf",
        "GEN_Nederland_NA31-1_Alpha.pdf",
        "GEN_Nederland_NA31-2_Alpha.pdf",
        "GEN_Nederland_NA14-2_Alpha.pdf",
        "GEN_Nederland_O7_North.pdf",
    ):
        write_pdf(tmp_path, name, one_page_pdf(name.encode()))

    handler = PDFFileHandler(FileSystemStorage(location=tmp_path))
    handler.run()
    assert handler.archive_gemeente_ids == {gemeente.id}

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
        filename = f"{category.value}_{region_name}_{document_type.removeprefix('PDF_')}_{region_name}.pdf"
        write_pdf(tmp_path, filename, one_page_pdf(filename.encode()))
        expected.add((csb.id, document_type))

    PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    attached = {(document.region_id, document.file_type) for document in ElectionDocument.objects.all()}
    assert attached == expected


def _board_with_shared_station(config, board_name, board_number):
    """The same Haarlemmermeer polling station as it is stored under one of its two waterschappen."""
    election = ElectionFactory(election_config=config, name=board_name, subcategory="AB2")
    board = RegionFactory(
        election=election,
        region_category=RegionCategory.WATERSCHAP,
        region_name=board_name,
        region_number=board_number,
    )
    municipality = RegionFactory(
        election=election,
        parent=board,
        csb=board,
        region_category=RegionCategory.GEMEENTE,
        region_name="Haarlemmermeer",
        region_number="394",
    )
    station = RegionFactory(
        election=election,
        parent=municipality,
        csb=board,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Don Bosco",
        region_number="0394::SB1",
    )
    return municipality, station


@pytest.mark.django_db
def test_csb_name_picks_the_region_when_it_also_serves_another_board(tmp_path):
    config = ElectionConfigFactory(identifier="AB2023", category=ElectionCategory.WS.value)
    _, rijnland_station = _board_with_shared_station(config, "Rijnland", "13")
    amstel_municipality, _ = _board_with_shared_station(config, "Amstel, Gooi en Vecht", "14")
    write_pdf(tmp_path, "AB2023_Rijnland_N10-1_0394::SB1.pdf", one_page_pdf(b"rijnland"))
    write_pdf(tmp_path, "AB2023_Amstel, Gooi en Vecht_NA31-2_Haarlemmermeer.pdf", one_page_pdf(b"amstel"))

    PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    file_type = ElectionDocument.FileType
    attached = {document.file_type: document.region for document in ElectionDocument.objects.all()}
    assert attached[file_type.PDF_N10_1] == rijnland_station
    assert attached[file_type.PDF_NA31_2] == amstel_municipality


@pytest.mark.django_db
def test_logs_a_bad_filename_and_imports_the_rest(tmp_path, caplog):
    barneveld()
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf")
    write_pdf(tmp_path, "TK2025_Nederland_NA31-2_Barneveld.pdf")

    with caplog.at_level(logging.ERROR):
        imported = PDFFileHandler(FileSystemStorage(location=tmp_path)).run()

    assert imported == 1
    assert ElectionDocument.objects.count() == 1
    assert "TK2025_NA31-2_Barneveld.pdf" in caplog.text
