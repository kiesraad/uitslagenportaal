"""Shared EMLBaseImporter behaviour: election resolve, hash dedupe, correction guard."""

from datetime import timedelta

import pytest

from election.models import Election, ElectionCategory, ElectionConfig, VoteCount
from election.tests.factories import ContestFactory, ElectionConfigFactory, ElectionFactory
from election.utils import visibility_cutoff
from eml_import.exceptions import EMLImporterException
from eml_import.models import ImportedEmlHash
from eml_import.tests.fakes import fake_eml_file
from eml_import.tests.test_eml_110_importer import CONFIG_IDENTIFIER, ELECTION_NAME
from eml_import.tests.test_eml_110_importer import make_eml as make_110a_eml
from eml_import.tests.test_eml_230_importer import (
    CONFIG_IDENTIFIER as CFG_230,
)
from eml_import.tests.test_eml_230_importer import (
    ELECTION_DATE as DATE_230,
)
from eml_import.tests.test_eml_230_importer import (
    ELECTION_NAME as NAME_230,
)
from eml_import.tests.test_eml_230_importer import (
    ELECTION_SUBCATEGORY,
    REGISTERED_NAME,
)
from eml_import.tests.test_eml_230_importer import (
    make_eml as make_230b_eml,
)
from eml_import.tests.test_eml_510_importer import (
    ELECTION_DATE as WS_DATE,
)
from eml_import.tests.test_eml_510_importer import (
    WS_CONFIG_IDENTIFIER,
    WS_ELECTION_NAME,
    make_ws_telling,
)
from eml_import.utils.eml_110_importer import EML110aImporter
from eml_import.utils.eml_230_importer import EML230bImporter
from eml_import.utils.eml_510_importer import EML510bImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.eml_type import EmlType
from party.models import Party
from party.tests.factories import PartyFactory
from region.models import Region
from region.tests.factories import RegionFactory


def _seed_counting_result(election):
    """Any current 510b/510d count blocks a later 110a/230b correction."""
    region = Region.objects.filter(election=election).first() or RegionFactory(election=election)
    party = Party.objects.filter(election=election).first() or PartyFactory(election=election, list_number=1)
    VoteCount.objects.create(
        contest=ContestFactory(election=election),
        region=region,
        party=party,
        valid_votes=1,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=EmlType.EML_510b,
    )


@pytest.mark.django_db
def test_resolves_election_config_from_identifier_prefix():
    """ElectionIdentifier/@Id may carry a suffix (e.g. re-election); only the prefix is the config id."""
    ElectionConfigFactory(identifier=CONFIG_IDENTIFIER)

    EML110aImporter(make_110a_eml(), fake_eml_file()).parse()

    election = Election.objects.get()
    assert election.election_config.identifier == CONFIG_IDENTIFIER
    assert election.name == ELECTION_NAME


@pytest.mark.django_db
def test_imports_against_an_expired_election_config():
    ElectionConfigFactory(
        identifier=CONFIG_IDENTIFIER,
        date=visibility_cutoff() - timedelta(days=1),
    )
    assert not ElectionConfig.objects.filter(identifier=CONFIG_IDENTIFIER).exists()

    EML110aImporter(make_110a_eml(), fake_eml_file()).parse()

    assert Election.objects.filter(election_config__identifier=CONFIG_IDENTIFIER).exists()


@pytest.mark.django_db
def test_raises_when_election_config_is_missing():
    eml_file = fake_eml_file("definitie.eml.xml")

    with pytest.raises(ElectionConfig.DoesNotExist):
        EML110aImporter(make_110a_eml(), eml_file)

    assert not Election.objects.exists()
    assert not ImportedEmlHash.objects.exists()


@pytest.mark.django_db
def test_records_hash_after_successful_import_and_skips_duplicate():
    ElectionConfigFactory(identifier=CONFIG_IDENTIFIER)
    content = b"<eml identical bytes/>"

    EML110aImporter(make_110a_eml(), NamedBytesIO(content, "definitie.eml.xml")).parse()
    assert ImportedEmlHash.objects.count() == 1
    region_ids = list(Region.objects.values_list("pk", flat=True))

    EML110aImporter(make_110a_eml(), NamedBytesIO(content, "other-name.eml.xml")).parse()

    assert ImportedEmlHash.objects.count() == 1
    # Duplicate short-circuits before correction; current regions are untouched
    assert list(Region.objects.values_list("pk", flat=True)) == region_ids


@pytest.mark.django_db
def test_failed_import_does_not_record_a_hash():
    config = ElectionConfigFactory(identifier=WS_CONFIG_IDENTIFIER, category=ElectionCategory.WS.value)
    ElectionFactory(
        election_config=config,
        name=WS_ELECTION_NAME,
        subcategory="AB2",
        date=WS_DATE,
    )
    eml = make_ws_telling(authority_id="0999", authority_name="Onbekend")

    with pytest.raises(EMLImporterException):
        EML510bImporter(eml, NamedBytesIO(b"<eml/>", "telling.eml.xml")).parse()

    assert not ImportedEmlHash.objects.exists()


@pytest.mark.django_db
def test_110a_correction_blocked_once_counting_results_exist():
    ElectionConfigFactory(identifier=CONFIG_IDENTIFIER)
    EML110aImporter(make_110a_eml(), fake_eml_file()).parse()
    _seed_counting_result(Election.objects.get())

    with pytest.raises(EMLImporterException, match="counting results already imported"):
        EML110aImporter(make_110a_eml(), fake_eml_file()).parse()


@pytest.mark.django_db
def test_230b_correction_blocked_once_counting_results_exist():
    config = ElectionConfigFactory(identifier=CFG_230)
    election = ElectionFactory(
        election_config=config,
        name=NAME_230,
        subcategory=ELECTION_SUBCATEGORY,
        date=DATE_230,
    )
    PartyFactory(election=election, registered_name=REGISTERED_NAME)
    EML230bImporter(make_230b_eml(), fake_eml_file()).parse()
    _seed_counting_result(election)

    with pytest.raises(EMLImporterException, match="counting results already imported"):
        EML230bImporter(make_230b_eml(), fake_eml_file()).parse()
