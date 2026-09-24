"""OSV4-3 CSVs are not imported as data, only stored as a document of the region they belong to."""

import pytest
from django.core.files.storage import default_storage

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.exceptions import EMLImporterException
from eml_import.models import ImportedEmlHash
from eml_import.tests.fakes import fake_osv43_csv
from eml_import.utils.csv_osv43_importer import CSVOsv43Importer
from eml_import.utils.github_eml_file_handler import GithubEmlFileHandler
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory

WS_ELECTION_NAME = "Algemeen bestuur van het waterschap Aa en Maas 2023"


@pytest.fixture
def ws_election():
    return ElectionFactory(
        election_config=ElectionConfigFactory(identifier="AB2023", category=ElectionCategory.WS.value),
        name=WS_ELECTION_NAME,
    )


@pytest.fixture
def ws_csb(ws_election):
    return RegionFactory(
        election=ws_election, region_category=RegionCategory.WATERSCHAP, region_number=None, region_name="Aa en Maas"
    )


def test_read_csv_header_from_buffer_stops_at_the_empty_row():
    csv = fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas", body='"Verkiezing";;"not a header"')

    assert CSVOsv43Importer.read_csv_header(csv) == {
        "Verkiezing": WS_ELECTION_NAME,
        "Datum": "2023-03-15",
        "Gebied": "Aa en Maas",
        "Nummer": "CSB",
    }
    assert not csv.closed
    assert csv.tell() == 0


def test_read_csv_header_from_path_strips_the_bom(tmp_path):
    path = tmp_path / "osv4-3_telling.csv"
    path.write_bytes(fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas").getvalue())

    assert list(CSVOsv43Importer.read_csv_header(path))[0] == "Verkiezing"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("category", "nummer", "gebied", "region_category", "region_number", "region_name"),
    [
        # A GR CSB is the gemeente itself, numbered, while the header only says "CSB"
        (ElectionCategory.GR, "CSB", "Almere", RegionCategory.GEMEENTE, "34", "Almere"),
        (ElectionCategory.TK, "HSB3", "Kieskring Zwolle", RegionCategory.KIESKRING, "3", "Zwolle"),
        (ElectionCategory.TK, "0034", "Gemeente Almere", RegionCategory.GEMEENTE, "34", "Almere"),
        (ElectionCategory.PS, "9003", "Openbaar lichaam Saba", RegionCategory.GEMEENTE, "9003", "Saba"),
    ],
)
def test_find_region_maps_nummer_and_gebied(category, nummer, gebied, region_category, region_number, region_name):
    election = ElectionFactory(election_config=ElectionConfigFactory(category=category.value))
    region = RegionFactory(
        election=election, region_category=region_category, region_number=region_number, region_name=region_name
    )
    # Same name, other category: must not make the lookup ambiguous
    RegionFactory(
        election=election,
        region_category=RegionCategory.PROVINCIE,
        region_number=region_number,
        region_name=region_name,
    )

    headers = {"Verkiezing": election.name, "Nummer": nummer, "Gebied": gebied}

    assert CSVOsv43Importer._find_region(election, headers) == region


@pytest.mark.django_db
def test_find_region_rejects_an_unknown_nummer(ws_csb):
    headers = {"Verkiezing": WS_ELECTION_NAME, "Nummer": "SB1", "Gebied": "Aa en Maas"}

    with pytest.raises(EMLImporterException, match="Unknown region number SB1"):
        CSVOsv43Importer._find_region(ws_csb.election, headers)


@pytest.mark.django_db
def test_find_region_rejects_a_region_missing_from_the_election_definition(ws_csb):
    headers = {"Verkiezing": WS_ELECTION_NAME, "Nummer": "CSB", "Gebied": "De Dommel"}

    with pytest.raises(EMLImporterException, match="De Dommel"):
        CSVOsv43Importer._find_region(ws_csb.election, headers)


@pytest.mark.django_db
def test_parse_rejects_an_unknown_election(ws_csb):
    csv = fake_osv43_csv("Algemeen bestuur van het waterschap De Dommel 2023", "CSB", "De Dommel")

    with pytest.raises(EMLImporterException, match="does not exist"):
        CSVOsv43Importer(csv).parse()

    assert not ImportedEmlHash.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "content",
    [
        b'"Lijstnummer";"Aanduiding"\r\n"1";"Partij"',
        # Recognised as OSV4-3 by the file handler, but without the Gebied the region cannot be found
        f'"Verkiezing";;"{WS_ELECTION_NAME}"\r\n"Nummer";;"CSB"\r\n\r\n'.encode(),
    ],
)
def test_parse_rejects_a_csv_without_the_osv43_header(ws_csb, content):
    with pytest.raises(EMLImporterException, match="Not a valid OSV4-3 CSV file"):
        CSVOsv43Importer(NamedBytesIO(content, "osv4-3_telling.csv")).parse()


@pytest.mark.django_db
def test_parse_stores_the_csv_as_a_current_document_of_the_region(ws_csb):
    csv = fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas")

    CSVOsv43Importer(csv).parse()

    document = ElectionDocument.objects.get()
    assert (document.region, document.file_type, document.content_type, document.size) == (
        ws_csb,
        ElectionDocument.FileType.CSV_OSV43,
        "text/csv",
        len(csv.getvalue()),
    )
    assert document.storage_key.startswith("AB2023/AB2023_Telling_OSV4-3_Aa_en_Maas_")
    assert document.storage_key.endswith(".csv")
    with default_storage.open(document.storage_key) as stored:
        assert stored.read() == csv.getvalue()
    assert ImportedEmlHash.objects.get().election == ws_csb.election


@pytest.mark.django_db
def test_parse_archives_the_previous_csv_of_the_region(ws_csb):
    CSVOsv43Importer(fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas", body="first")).parse()
    first = ElectionDocument.objects.get()

    CSVOsv43Importer(fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas", body="corrected")).parse()

    current = ElectionDocument.objects.get()
    assert current.pk != first.pk
    first.refresh_from_db()
    assert first.is_current is False


@pytest.mark.django_db
def test_parse_skips_a_csv_with_identical_bytes(ws_csb):
    CSVOsv43Importer(fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas")).parse()

    CSVOsv43Importer(fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas", filename="renamed.csv")).parse()

    assert ElectionDocument.all_objects.count() == 1


@pytest.mark.django_db
def test_github_handler_imports_a_csv_from_the_buffer_it_classified(ws_csb):
    csv = fake_osv43_csv(WS_ELECTION_NAME, "CSB", "Aa en Maas")

    GithubEmlFileHandler(ws_csb.election.election_config).import_file_objects([csv])

    assert ElectionDocument.objects.get().region == ws_csb
