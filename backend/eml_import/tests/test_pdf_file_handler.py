import hashlib
import logging
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage, storages

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.models import ImportedFileHash
from eml_import.tests.pdf_files import PDF_BYTES, barneveld, one_page_pdf, pv_pdf, write_pdf
from eml_import.utils.pdf_file_handler import LOCK_TIMEOUT, PDFFileHandler
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory


def warnings_of(caplog) -> list[str]:
    """The warnings the file handler logged, which is the only trace a lock problem leaves."""
    return [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]


@pytest.mark.django_db
def test_imports_a_municipal_certified_document_onto_the_gemeente():
    region = barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")

    handler = PDFFileHandler(storages["pv_import"])
    handler.run()

    document = ElectionDocument.objects.get()
    assert handler.archive_municipality_ids == set()
    assert document.region == region
    assert document.file_type == ElectionDocument.FileType.PDF_NA31_2
    assert document.content_type == "application/pdf"
    assert document.size == len(PDF_BYTES)
    assert default_storage.open(document.storage_key).read() == PDF_BYTES
    preview_key = Path(document.storage_key).with_suffix(".png").as_posix()
    assert default_storage.open(preview_key).read().startswith(b"\x89PNG\r\n\x1a\n")
    assert not storages["pv_import"].exists("TK2025_Nederland_NA31-2_Barneveld.pdf")


@pytest.mark.django_db
def test_records_the_hash_and_skips_bytes_that_were_already_imported():
    region = barneveld()
    name = "TK2025_Nederland_NA31-2_Barneveld.pdf"
    write_pdf(name)
    handler = PDFFileHandler(storages["pv_import"])

    assert handler.run() == 1
    recorded = ImportedFileHash.objects.get()
    assert recorded.election == region.election
    assert recorded.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert not storages["pv_import"].exists(name)

    write_pdf(name)
    assert handler.run() == 0
    assert ElectionDocument.objects.count() == 1
    assert not storages["pv_import"].exists(name)


@pytest.mark.django_db
def test_deletes_a_processed_pdf_from_a_subfolder_of_the_import_storage():
    barneveld()
    key = "nested/TK2025_Nederland_NA31-2_Barneveld.pdf"
    write_pdf(key)

    PDFFileHandler(storages["pv_import"]).run()

    assert not storages["pv_import"].exists(key)
    assert default_storage.open(ElectionDocument.objects.get().storage_key).read() == PDF_BYTES


@pytest.mark.django_db
def test_keeps_the_imported_document_when_the_inbox_delete_fails(monkeypatch, caplog):
    barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(storages["pv_import"])

    def fail_delete(_name):
        raise OSError("inbox unavailable")

    monkeypatch.setattr(handler.storage, "delete", fail_delete)

    with caplog.at_level(logging.ERROR):
        assert handler.run() == 1

    assert ElectionDocument.objects.count() == 1
    assert storages["pv_import"].exists("TK2025_Nederland_NA31-2_Barneveld.pdf")
    assert "Failed to delete processed proces-verbaal" in caplog.text


@pytest.mark.django_db
def test_a_rescanned_proces_verbaal_supersedes_the_one_it_replaces():
    region = barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf", pv_pdf(b"first scan"))
    PDFFileHandler(storages["pv_import"]).run()
    superseded = ElectionDocument.objects.get()

    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf", pv_pdf(b"second scan"))
    assert PDFFileHandler(storages["pv_import"]).run() == 1

    current = ElectionDocument.objects.get(region=region)
    assert current.pk != superseded.pk
    assert default_storage.open(current.storage_key).read() == pv_pdf(b"second scan")
    superseded.refresh_from_db()
    assert superseded.is_current is False


@pytest.mark.django_db
def test_every_correction_on_one_form_stays_current():
    region = barneveld()
    write_pdf("TK2025_Nederland_NA14-2_Barneveld.pdf", pv_pdf(b"first correction", PvModel="NA14-2"))
    PDFFileHandler(storages["pv_import"]).run()

    write_pdf("TK2025_Nederland_NA14-2_Barneveld.pdf", pv_pdf(b"second correction", PvModel="NA14-2"))
    assert PDFFileHandler(storages["pv_import"]).run() == 1

    corrections = ElectionDocument.objects.filter(region=region).order_by("created_at", "pk")
    assert [default_storage.open(document.storage_key).read() for document in corrections] == [
        pv_pdf(b"first correction", PvModel="NA14-2"),
        pv_pdf(b"second correction", PvModel="NA14-2"),
    ]
    # Shared region and file type, so the download names have to part on their timestamp
    assert len({document.download_filename for document in corrections}) == 2


@pytest.mark.django_db
def test_imports_a_polling_station_certified_document_by_stembureau_id():
    gemeente = barneveld()
    station = RegionFactory(
        election=gemeente.election,
        parent=gemeente,
        csb=gemeente.csb,
        region_category=RegionCategory.STEMBUREAU,
        region_name="Gemeentehuis",
        region_number="0203::SB1",
    )
    write_pdf("TK2025_Nederland_N10-1_0203::SB1.pdf", pv_pdf(PvModel="N10-1", PvStembureau="1"))

    handler = PDFFileHandler(storages["pv_import"])
    handler.run()

    document = ElectionDocument.objects.get()
    assert document.region == station
    assert document.file_type == ElectionDocument.FileType.PDF_N10_1
    assert handler.archive_municipality_ids == {gemeente.id}


@pytest.mark.django_db
def test_imports_sb_gsb_and_hsb_documents_onto_those_bodies():
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
    for model, region_name, stembureau in (
        ("N10-1", "Alpha", "1"),
        ("N10-2", "Alpha", "1"),
        ("NA14-1", "Alpha", "1"),
        ("NA31-1", "Alpha", ""),
        ("NA31-2", "Alpha", ""),
        ("NA14-2", "Alpha", ""),
        ("O7", "North", ""),
    ):
        write_pdf(
            f"{model}.pdf",
            pv_pdf(
                model.encode(),
                PvElection="GEN",
                PvModel=model,
                PvRegionName=region_name,
                PvStembureau=stembureau,
            ),
        )

    handler = PDFFileHandler(storages["pv_import"])
    handler.run()
    assert handler.archive_municipality_ids == {gemeente.id}

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
def test_imports_p22_onto_the_csb_of_that_election():
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
        write_pdf(
            f"{category.value}.pdf",
            pv_pdf(
                category.value.encode(),
                PvElection=category.value,
                PvModel=document_type.removeprefix("PDF_"),
                PvRegionName=region_name,
            ),
        )
        expected.add((csb.id, document_type))

    PDFFileHandler(storages["pv_import"]).run()

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
def test_csb_name_picks_the_region_when_it_also_serves_another_board():
    config = ElectionConfigFactory(identifier="AB2023", category=ElectionCategory.WS.value)
    _, rijnland_station = _board_with_shared_station(config, "Rijnland", "13")
    amstel_municipality, _ = _board_with_shared_station(config, "Amstel, Gooi en Vecht", "14")
    write_pdf(
        "n10.pdf",
        pv_pdf(
            b"rijnland",
            PvElection="AB2023",
            PvModel="N10-1",
            PvRegionName="Haarlemmermeer",
            PvCsb="Rijnland",
            PvStembureau="1",
        ),
    )
    write_pdf(
        "na31.pdf",
        pv_pdf(
            b"amstel",
            PvElection="AB2023",
            PvModel="NA31-2",
            PvRegionName="Haarlemmermeer",
            PvCsb="Amstel, Gooi en Vecht",
        ),
    )

    PDFFileHandler(storages["pv_import"]).run()

    file_type = ElectionDocument.FileType
    attached = {document.file_type: document.region for document in ElectionDocument.objects.all()}
    assert attached[file_type.PDF_N10_1] == rijnland_station
    assert attached[file_type.PDF_NA31_2] == amstel_municipality


@pytest.mark.django_db
def test_logs_a_waterschap_polling_station_form_without_csb(caplog):
    config = ElectionConfigFactory(identifier="AB2023", category=ElectionCategory.WS.value)
    _board_with_shared_station(config, "Rijnland", "13")
    write_pdf("n10.pdf", pv_pdf(PvElection="AB2023", PvModel="N10-1", PvRegionName="Haarlemmermeer", PvStembureau="1"))

    with caplog.at_level(logging.ERROR):
        imported = PDFFileHandler(storages["pv_import"]).run()

    assert imported == 0
    assert "needs PvCsb" in caplog.text
    assert storages["pv_import"].exists("n10.pdf")


@pytest.mark.django_db
def test_logs_a_pdf_missing_identity_and_imports_the_rest(caplog):
    barneveld()
    write_pdf("blank.pdf", one_page_pdf(b"blank"))
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")

    with caplog.at_level(logging.ERROR):
        imported = PDFFileHandler(storages["pv_import"]).run()

    assert imported == 1
    assert ElectionDocument.objects.count() == 1
    assert "blank.pdf" in caplog.text
    assert storages["pv_import"].exists("blank.pdf")
    assert not storages["pv_import"].exists("TK2025_Nederland_NA31-2_Barneveld.pdf")


@pytest.mark.django_db
def test_run_skips_the_import_while_another_worker_holds_the_lock(caplog):
    barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(storages["pv_import"])

    with cache.lock(handler.cache_lock_key(), timeout=LOCK_TIMEOUT):
        imported = handler.run()

    assert imported == 0
    assert ElectionDocument.objects.count() == 0
    assert handler.archive_municipality_ids == set()
    assert warnings_of(caplog) == ["Could not acquire lock, PDFFileHandler is already running"]


@pytest.mark.django_db
def test_run_releases_the_lock_when_it_finishes():
    barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(storages["pv_import"])

    handler.run()

    assert cache.lock(handler.cache_lock_key(), blocking=False).acquire() is True


@pytest.mark.django_db
def test_run_holds_a_lock_that_expires_on_its_own(monkeypatch):
    """A worker that dies mid-import must not block the next sweep forever."""
    barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(storages["pv_import"])
    remaining = []
    original = PDFFileHandler._import_pv

    def observe_ttl(self, file):
        remaining.append(cache.ttl(self.cache_lock_key()))
        return original(self, file)

    monkeypatch.setattr(PDFFileHandler, "_import_pv", observe_ttl)

    handler.run()

    assert remaining == [LOCK_TIMEOUT]


@pytest.mark.django_db
def test_run_keeps_its_result_when_the_lock_expires_mid_import(monkeypatch, caplog):
    barneveld()
    write_pdf("TK2025_Nederland_NA31-2_Barneveld.pdf")
    handler = PDFFileHandler(storages["pv_import"])
    original = PDFFileHandler._import_pv

    def expire_lock(self, file):
        cache.delete(self.cache_lock_key())
        return original(self, file)

    monkeypatch.setattr(PDFFileHandler, "_import_pv", expire_lock)

    imported = handler.run()

    assert imported == 1
    assert ElectionDocument.objects.count() == 1
    assert warnings_of(caplog) == ["Lock expired while importing proces-verbalen"]
