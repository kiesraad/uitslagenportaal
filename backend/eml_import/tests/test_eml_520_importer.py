"""EML 520 files are not imported as data, only stored as a document of the election's CSB."""

import pytest
from django.core.files.storage import default_storage

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.exceptions import EMLImporterException
from eml_import.models import ImportedFileHash
from eml_import.tests.fakes import fake_520_eml
from eml_import.utils.eml_520_importer import EML520Importer
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


def test_read_election_fields_from_buffer_rewinds():
    eml = fake_520_eml("AB2023_17", WS_ELECTION_NAME)

    assert EML520Importer._read_election_fields(eml) == ("AB2023_17", WS_ELECTION_NAME)
    assert not eml.closed
    assert eml.tell() == 0


def test_read_election_fields_from_path_ignores_namespaces(tmp_path):
    path = tmp_path / "resultaat.eml.xml"
    path.write_text(
        "<EML xmlns='urn:oasis:names:tc:evs:schema:eml' Id='520'>"
        "<ElectionIdentifier Id='AB2023'>"
        f"<ElectionName>{WS_ELECTION_NAME}</ElectionName>"
        "</ElectionIdentifier>"
        "</EML>"
    )

    assert EML520Importer._read_election_fields(path) == ("AB2023", WS_ELECTION_NAME)


@pytest.mark.django_db
def test_parse_rejects_an_unknown_election_config(ws_csb):
    with pytest.raises(EMLImporterException, match="ElectionConfig does not exist for AB9999"):
        EML520Importer(fake_520_eml("AB9999", WS_ELECTION_NAME)).parse()

    assert not ImportedFileHash.objects.exists()


@pytest.mark.django_db
def test_parse_rejects_an_unknown_election(ws_csb):
    with pytest.raises(EMLImporterException, match="does not exist"):
        EML520Importer(fake_520_eml("AB2023", "Algemeen bestuur van het waterschap De Dommel 2023")).parse()

    assert not ImportedFileHash.objects.exists()


@pytest.mark.django_db
def test_parse_rejects_a_file_without_election_fields(ws_csb):
    with pytest.raises(EMLImporterException, match="Not a valid EML 520 file"):
        EML520Importer(NamedBytesIO(b"<EML Id='520'/>", "resultaat.eml.xml")).parse()


@pytest.mark.django_db
def test_parse_rejects_a_missing_csb(ws_election):
    with pytest.raises(EMLImporterException, match="CSB region does not exist"):
        EML520Importer(fake_520_eml("AB2023", WS_ELECTION_NAME)).parse()

    assert not ImportedFileHash.objects.exists()


@pytest.mark.django_db
def test_parse_stores_the_eml_as_a_current_document_of_the_csb(ws_csb):
    eml = fake_520_eml("AB2023_17", WS_ELECTION_NAME)

    EML520Importer(eml).parse()

    document = ElectionDocument.objects.get()
    assert (document.region, document.file_type, document.content_type, document.size) == (
        ws_csb,
        ElectionDocument.FileType.EML_520,
        "application/xml",
        len(eml.getvalue()),
    )
    assert document.storage_key.startswith("AB2023/AB2023_Resultaat_Aa_en_Maas_")
    assert document.storage_key.endswith(".eml.xml")
    with default_storage.open(document.storage_key) as stored:
        assert stored.read() == eml.getvalue()
    assert ImportedFileHash.objects.get().election == ws_csb.election


@pytest.mark.django_db
def test_parse_archives_the_previous_520_of_the_region(ws_csb):
    EML520Importer(fake_520_eml("AB2023", WS_ELECTION_NAME, extra="<n>1</n>")).parse()
    first = ElectionDocument.objects.get()

    EML520Importer(fake_520_eml("AB2023", WS_ELECTION_NAME, extra="<n>2</n>")).parse()

    current = ElectionDocument.objects.get()
    assert current.pk != first.pk
    first.refresh_from_db()
    assert first.is_current is False


@pytest.mark.django_db
def test_parse_skips_a_520_with_identical_bytes(ws_csb):
    EML520Importer(fake_520_eml("AB2023", WS_ELECTION_NAME)).parse()

    EML520Importer(fake_520_eml("AB2023", WS_ELECTION_NAME, filename="renamed.eml.xml")).parse()

    assert ElectionDocument.all_objects.count() == 1


@pytest.mark.django_db
def test_github_handler_imports_a_520_from_the_buffer_it_classified(ws_csb):
    eml = fake_520_eml("AB2023", WS_ELECTION_NAME)

    GithubEmlFileHandler(ws_csb.election.election_config).import_file_objects([eml])

    assert ElectionDocument.objects.get().region == ws_csb
