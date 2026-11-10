"""EML 520 files are not imported as data, only stored as a document of the election's CSB."""

from datetime import date

import pytest
from django.core.files.storage import default_storage
from pyeml_bindings import (
    AuthorityAddressStructure,
    AuthorityIdentifierStructureKr,
    ElectionCategoryType,
    ElectionDate,
    ElectionIdentifierStructure520,
    ElectionSubcategory,
    ElectionSubcategoryType,
    Eml520,
    ManagingAuthorityStructureKr,
    Result,
    TransactionId,
)
from xsdata.models.datatype import XmlDate

from election.models import ElectionCategory, ElectionDocument
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.exceptions import EMLImporterException
from eml_import.models import ImportedFileHash
from eml_import.tests.fakes import fake_eml_file
from eml_import.utils.eml_520_importer import EML520Importer
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from region.tests.factories import RegionFactory

WS_ELECTION_NAME = "Algemeen bestuur van het waterschap Aa en Maas 2023"


def make_eml(election_id: str = "AB2023_Aa_en_Maas") -> Eml520:
    """A 520 document. Its result is left empty: the importer only reads the election identifier."""
    return Eml520(
        schema_version="5",
        transaction_id=TransactionId(value="1"),
        managing_authority=ManagingAuthorityStructureKr(
            authority_identifier=AuthorityIdentifierStructureKr(id="CSB", value="Aa en Maas"),
            authority_address=AuthorityAddressStructure(),
        ),
        result=Result(
            election=Result.Election(
                election_identifier=ElectionIdentifierStructure520(
                    id=election_id,
                    election_name=WS_ELECTION_NAME,
                    election_category=ElectionCategoryType.AB,
                    election_subcategory=[ElectionSubcategory(value=ElectionSubcategoryType.AB2)],
                    election_date=[ElectionDate(value=XmlDate.from_date(date(2023, 3, 15)))],
                )
            )
        ),
    )


@pytest.fixture
def ws_election():
    return ElectionFactory(
        election_config=ElectionConfigFactory(identifier="AB2023", category=ElectionCategory.WS.value),
        name=WS_ELECTION_NAME,
        subcategory=ElectionSubcategoryType.AB2.value,
    )


@pytest.fixture
def ws_csb(ws_election):
    return RegionFactory(
        election=ws_election, region_category=RegionCategory.WATERSCHAP, region_number=None, region_name="Aa en Maas"
    )


@pytest.mark.django_db
def test_rejects_an_unknown_election_config(ws_csb):
    with pytest.raises(EMLImporterException, match="ElectionConfig does not exist for AB9999"):
        EML520Importer(fake_eml_file(), eml=make_eml("AB9999")).parse()


@pytest.mark.django_db
def test_parse_rejects_a_missing_csb(ws_election):
    with pytest.raises(EMLImporterException, match="CSB region does not exist"):
        EML520Importer(fake_eml_file(), eml=make_eml()).parse()

    assert not ImportedFileHash.objects.exists()


@pytest.mark.django_db
def test_parse_stores_the_eml_as_a_current_document_of_the_csb(ws_csb):
    eml_file = fake_eml_file("resultaat.eml.xml")

    EML520Importer(eml_file, eml=make_eml()).parse()

    document = ElectionDocument.objects.get()
    assert (document.region, document.file_type, document.content_type, document.size) == (
        ws_csb,
        ElectionDocument.FileType.EML_520,
        "application/xml",
        len(eml_file.getvalue()),
    )
    assert document.storage_key.startswith("AB2023/AB2023_Resultaat_Aa_en_Maas_")
    assert document.storage_key.endswith(".eml.xml")
    with default_storage.open(document.storage_key) as stored:
        assert stored.read() == eml_file.getvalue()
    assert ImportedFileHash.objects.get().election == ws_csb.election


@pytest.mark.django_db
def test_parse_archives_the_previous_520_of_the_region(ws_csb):
    EML520Importer(fake_eml_file(), eml=make_eml()).parse()
    first = ElectionDocument.objects.get()

    EML520Importer(fake_eml_file(), eml=make_eml()).parse()

    current = ElectionDocument.objects.get()
    assert current.pk != first.pk
    first.refresh_from_db()
    assert first.is_current is False


@pytest.mark.django_db
def test_parse_skips_a_520_with_identical_bytes(ws_csb):
    EML520Importer(NamedBytesIO(b"<EML Id='520'/>", "resultaat.eml.xml"), eml=make_eml()).parse()

    EML520Importer(NamedBytesIO(b"<EML Id='520'/>", "renamed.eml.xml"), eml=make_eml()).parse()

    assert ElectionDocument.all_objects.count() == 1
