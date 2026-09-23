from pathlib import Path

import pytest
from django.core.files.storage import default_storage
from django.db import IntegrityError

from election.models import CertifiedElectionDocument, ElectionCategory
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.exceptions import EMLImporterException
from eml_import.utils.folder_pdf_file_handler import FolderPDFFileHanlder
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory

PDF_BYTES = b"%PDF-1.7 barneveld"


def write_pdf(folder: Path, name: str, content: bytes = PDF_BYTES) -> Path:
    path = folder / name
    path.write_bytes(content)
    return path


@pytest.mark.django_db
def test_imports_a_municipal_proces_verbaal_onto_the_gemeente(tmp_path):
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


@pytest.mark.django_db
def test_rejects_a_second_proces_verbaal_for_the_same_region_and_type(tmp_path):
    config = ElectionConfigFactory(identifier="TK2025", category=ElectionCategory.TK.value)
    election = ElectionFactory(election_config=config, subcategory="TK")
    RegionFactory(
        election=election,
        region_category=RegionCategory.GEMEENTE,
        region_name="Barneveld",
        region_number="203",
    )
    first = b"%PDF-1.7 first"
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf", first)
    FolderPDFFileHanlder(tmp_path).run()
    write_pdf(tmp_path, "TK2025_NA31-2_Barneveld.pdf", b"%PDF-1.7 replaced")

    with pytest.raises(IntegrityError):
        FolderPDFFileHanlder(tmp_path).run()

    document = CertifiedElectionDocument.objects.get()
    assert document.size == len(first)
    assert default_storage.open(document.storage_key).read() == first


@pytest.mark.django_db
def test_imports_a_polling_station_proces_verbaal_by_stembureau_id(tmp_path):
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

    with pytest.raises(EMLImporterException, match="does not match"):
        FolderPDFFileHanlder(tmp_path).run()

    assert CertifiedElectionDocument.objects.count() == 0
