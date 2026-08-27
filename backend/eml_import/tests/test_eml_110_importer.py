from datetime import date

import pytest
from pyeml_bindings import (
    ContestIdentifierStructure110A,
    ElectionCategoryType,
    ElectionDate,
    ElectionEvent,
    ElectionIdentifierStructure110A,
    ElectionSubcategory,
    ElectionSubcategoryType,
    ElectionTree,
    Eml110a,
    MaxVotes,
    RegionCategoryType,
    RegionName,
    RegisteredAppellation,
    RegisteredParties,
    RegisteredParty,
    TransactionId,
    VotingMethod,
)
from pyeml_bindings import (
    Region as EmlRegion,
)
from xsdata.models.datatype import XmlDate

from election.models import Election
from election.tests.factories import ElectionConfigFactory
from eml_import.tests.helpers import fake_eml_file
from eml_import.utils.eml_110_importer import EML110aImporter
from mainsite.models import RegionCategory
from party.models import Party
from region.models import Region

ELECTION_ID = "AB2023_Scheldestromen"
CONFIG_IDENTIFIER = "AB2023"
ELECTION_NAME = "Algemeen bestuur van het waterschap Scheldestromen 2023"
ELECTION_DATE = date(2023, 3, 15)
CONTEST_ID = "geen"


def make_region(number, category, name, parent_number=None, parent_category=None) -> EmlRegion:
    """One kr:Region node; parent_* mirror SuperiorRegionNumber/SuperiorRegionCategory."""
    return EmlRegion(
        region_number=number,
        region_category=category,
        region_name=RegionName(value=name),
        superior_region_number=parent_number,
        superior_region_category=parent_category,
    )


# A three-level tree, parents first: _parse_regions() looks a parent up as it goes.
ELECTION_TREE = [
    make_region(17, RegionCategoryType.WATERSCHAP, "Scheldestromen"),
    make_region(1, RegionCategoryType.KIESKRING, "Scheldestromen", 17, RegionCategoryType.WATERSCHAP),
    make_region(654, RegionCategoryType.GEMEENTE, "Borsele", 1, RegionCategoryType.KIESKRING),
]


def make_eml(*, regions: list[EmlRegion] | None = None, parties=("CDA",), contest_id=CONTEST_ID) -> Eml110a:
    """A 110a document. Everything the importer does not read is filled in with constants."""
    if regions is None:
        regions = ELECTION_TREE

    return Eml110a(
        schema_version="5",
        transaction_id=TransactionId(value="1"),
        election_event=ElectionEvent(
            election=ElectionEvent.Election(
                election_identifier=ElectionIdentifierStructure110A(
                    id=ELECTION_ID,
                    election_name=ELECTION_NAME,
                    election_category=ElectionCategoryType.AB,
                    election_subcategory=[ElectionSubcategory(value=ElectionSubcategoryType.AB2)],
                    election_date=[ElectionDate(value=XmlDate.from_date(ELECTION_DATE))],
                ),
                contest=ElectionEvent.Election.Contest(
                    contest_identifier=ContestIdentifierStructure110A(id=contest_id),
                    voting_method=VotingMethod(value="SPV"),
                    max_votes=MaxVotes(value=1),
                ),
                election_tree=ElectionTree(region=list(regions)),
                registered_parties=RegisteredParties(
                    registered_party=[
                        RegisteredParty(registered_appellation=RegisteredAppellation(value=name)) for name in parties
                    ]
                ),
            )
        ),
    )


@pytest.fixture
def election_config(db):
    """_parse_election() looks the config up by the part of ElectionIdentifier/@Id before the "_"."""
    return ElectionConfigFactory(identifier=CONFIG_IDENTIFIER)


@pytest.fixture
def election(election_config):
    """The Election created by importing the default document."""
    EML110aImporter(make_eml(), fake_eml_file()).parse()
    return Election.objects.get(election_config=election_config)


@pytest.fixture
def regions(election):
    """The imported regions, keyed by category; the tree has one region per category."""
    return {region.region_category: region for region in Region.objects.filter(election=election)}


def test_creates_election_from_identifier(election_config):
    EML110aImporter(make_eml(), fake_eml_file()).parse()

    election = Election.objects.get(election_config=election_config)
    assert election.name == ELECTION_NAME
    assert election.subcategory == "AB2"
    assert election.date == ELECTION_DATE


def test_creates_region_tree_with_parents(election, regions):
    waterschap = regions[RegionCategory.WATERSCHAP]
    kieskring = regions[RegionCategory.KIESKRING]
    gemeente = regions[RegionCategory.GEMEENTE]

    assert Region.objects.filter(election=election).count() == 3
    assert (waterschap.region_number, waterschap.region_name) == ("17", "Scheldestromen")
    assert (gemeente.region_number, gemeente.region_name) == ("654", "Borsele")
    assert waterschap.parent is None
    assert kieskring.parent == waterschap
    assert gemeente.parent == kieskring


def test_csb_is_the_election_tree_root(regions):
    waterschap = regions[RegionCategory.WATERSCHAP]

    assert waterschap.csb is None
    assert regions[RegionCategory.KIESKRING].csb == waterschap
    # The gemeente inherits the root from its parent rather than pointing at the kieskring
    assert regions[RegionCategory.GEMEENTE].csb == waterschap


def test_creates_registered_parties(election_config):
    EML110aImporter(make_eml(parties=("Partij voor Zeeland", "CDA")), fake_eml_file()).parse()

    election = Election.objects.get(election_config=election_config)
    names = Party.objects.filter(election=election).values_list("registered_name", flat=True)
    assert set(names) == {"Partij voor Zeeland", "CDA"}


def test_correction_deletes_prior_regions_and_parties(election_config):
    eml = make_eml(parties=("Partij voor Zeeland", "CDA"))

    EML110aImporter(eml, fake_eml_file()).parse()
    election = Election.objects.get(election_config=election_config)
    original_region_ids = set(Region.objects.filter(election=election).values_list("pk", flat=True))
    original_party_ids = set(Party.objects.filter(election=election).values_list("pk", flat=True))

    EML110aImporter(eml, fake_eml_file()).parse()

    assert Region.objects.filter(election=election).count() == 3
    assert Party.objects.filter(election=election).count() == 2
    assert not Region.objects.filter(pk__in=original_region_ids).exists()
    assert not Party.objects.filter(pk__in=original_party_ids).exists()
