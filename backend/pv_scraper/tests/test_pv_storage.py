import pytest
from django.core.files.storage import storages
from pypdf import PdfReader

from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from pv_ocr.tests.classified_pvs import BLANK_PDF, EDE_12, blank_pdf, classified
from pv_ocr.utils.pv_classifier import PvClassificationException, PvClassifier, PvElection, PvRegion
from pv_scraper.tests.factories import ScrapeSourceFactory
from pv_scraper.utils.pv_storage import STORAGE_ENTRY, save_to_storage


@pytest.mark.django_db
@pytest.mark.parametrize("region", [PvRegion(code="0228", stembureau="12"), PvRegion(name="ede", stembureau="12")])
def test_save_to_storage_names_the_gemeente_as_its_source_does(region):
    source = ScrapeSourceFactory(code="gm0228", name="Ede")

    key = save_to_storage(classified("N 10-2", PvElection("GR2026"), region), source, "pvs")

    assert key == "pvs/GR2026_N10-2_0228-ede_SB12.pdf"
    assert PdfReader(storages[STORAGE_ENTRY].open(key)).metadata["/PvRegionName"] == "Ede"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("election", "region"),
    [
        (PvElection("GR2026"), PvRegion(code="0289", name="Wageningen")),
        # A GR header naming another gemeente.
        (PvElection("GR2026", authority="Tiel"), EDE_12),
        # A PV that names no gemeente at all.
        (PvElection("GR2026"), PvRegion(stembureau="12")),
    ],
)
def test_save_to_storage_refuses_a_pv_of_another_gemeente(election, region):
    source = ScrapeSourceFactory(code="gm0228", name="Ede")

    with pytest.raises(PvClassificationException):
        save_to_storage(classified("N 10-2", election, region), source, "pvs")


@pytest.mark.django_db
def test_save_to_storage_takes_the_gemeente_a_gr_header_names():
    source = ScrapeSourceFactory(code="gm0228", name="Ede")

    key = save_to_storage(classified("P 22-2", PvElection("GR2026", authority="Ede"), PvRegion()), source, "pvs")

    assert key == "pvs/GR2026_P22-2_0228-ede.pdf"


@pytest.mark.django_db
def test_save_to_storage_needs_a_classified_pv():
    with pytest.raises(PvClassificationException):
        save_to_storage(PvClassifier(NamedBytesIO(BLANK_PDF, "pv.pdf")), ScrapeSourceFactory(), "pvs")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "name", "election", "csb"),
    [
        (RegionCategory.WATERSCHAP, "Vallei en Veluwe", "AB2027", "vallei-en-veluwe"),
        # A source may be named with what kind of authority it is.
        (RegionCategory.WATERSCHAP, "Waterschap Limburg", "AB2027", "limburg"),
        (RegionCategory.WATERSCHAP, "Hoogheemraadschap van Delfland", "AB2027", "delfland"),
        (RegionCategory.WATERSCHAP, "Wetterskip Fryslân", "AB2027", "fryslan"),
        (RegionCategory.PROVINCIE, "Provincie Drenthe", "PS2027", "drenthe"),
    ],
)
def test_save_to_storage_takes_the_csb_from_a_waterschap_or_province_source(kind, name, election, csb):
    source = ScrapeSourceFactory(code="ws0665", kind=kind, name=name)

    key = save_to_storage(classified("N 10-2", PvElection(election), EDE_12), source, "pvs")

    assert key == f"pvs/{election}_N10-2_{csb}_0228-ede_SB12.pdf"


@pytest.mark.django_db
def test_save_to_storage_stores_a_hoofdstembureau_model_under_its_kieskring():
    # The gemeente where the hoofdstembureau sits publishes the PV of its kieskring.
    source = ScrapeSourceFactory(code="gm0202", name="Arnhem")
    region = PvRegion(kieskring="1", kieskring_name="Arnhem")

    key = save_to_storage(classified("O 7", PvElection("PS2023", authority="Gelderland"), region), source, "pvs")

    assert key == "pvs/PS2023_O7_gelderland_kieskring-1-arnhem.pdf"
    metadata = PdfReader(storages[STORAGE_ENTRY].open(key)).metadata
    # The region code is the kieskring's number, its name the kieskring's name.
    assert (metadata["/Title"], metadata["/PvRegionCode"], metadata["/PvRegionName"]) == (
        "O7 kieskring 1 Arnhem",
        "1",
        "Arnhem",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "code", "name", "election"),
    [
        (RegionCategory.WATERSCHAP, "ws0665", "Vallei en Veluwe", PvElection("AB2027")),
        # A gemeente's website may publish the PV of its waterschap.
        (RegionCategory.GEMEENTE, "gm0289", "Wageningen", PvElection("AB2027", authority="Vallei en Veluwe")),
    ],
)
def test_save_to_storage_stores_a_csb_model_under_its_csb(kind, code, name, election):
    source = ScrapeSourceFactory(code=code, kind=kind, name=name)

    key = save_to_storage(classified("P 22-2", election, PvRegion()), source, "pvs")

    assert key == "pvs/AB2027_P22-2_vallei-en-veluwe.pdf"
    metadata = PdfReader(storages[STORAGE_ENTRY].open(key)).metadata
    assert (metadata["/Title"], metadata["/PvCsb"], metadata["/PvRegionName"]) == (
        "P22-2 Vallei en Veluwe",
        "Vallei en Veluwe",
        "Vallei en Veluwe",
    )
    assert "/PvRegionCode" not in metadata


@pytest.mark.django_db
def test_save_to_storage_replaces_a_file_of_the_same_name():
    source = ScrapeSourceFactory(code="gm0228", name="Ede")
    save_to_storage(classified("N 10-2", PvElection("GR2026"), EDE_12), source, "pvs")
    newer = classified("N 10-2", PvElection("GR2026"), EDE_12)
    newer_pdf = blank_pdf(width=100)
    newer.file = NamedBytesIO(newer_pdf, "pv.pdf")

    key = save_to_storage(newer, source, "pvs")

    assert storages[STORAGE_ENTRY].listdir("pvs")[1] == ["GR2026_N10-2_0228-ede_SB12.pdf"]
    assert storages[STORAGE_ENTRY].open(key).read().startswith(newer_pdf)
