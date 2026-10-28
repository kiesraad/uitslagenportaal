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

from election.models import Contest, Election
from election.tests.factories import ElectionConfigFactory
from eml_import.exceptions import EMLImporterException
from eml_import.tests.fakes import fake_eml_file
from eml_import.tests.test_eml_230_importer import CONTEST_NAME, make_affiliation, make_candidate
from eml_import.tests.test_eml_230_importer import make_eml as make_230b_eml
from eml_import.utils.eml_110_importer import EML110aImporter, EML110bImporter
from eml_import.utils.eml_230_importer import EML230bImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from party.models import Party
from party.tests.factories import PartyFactory
from region.models import Region
from region.tests.factories import RegionFactory

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


def make_eml(*, regions: list[EmlRegion] | None = None, contest_id=CONTEST_ID) -> Eml110a:
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
                    registered_party=[RegisteredParty(registered_appellation=RegisteredAppellation(value="CDA"))]
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
    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()
    return Election.objects.get(election_config=election_config)


@pytest.fixture
def regions(election):
    """The imported regions, keyed by category; the tree has one region per category."""
    return {region.region_category: region for region in Region.objects.filter(election=election)}


def test_creates_election_from_identifier(election_config):
    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

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


def test_kieskring_hangs_under_a_staat_without_a_region_number(election_config):
    """In TK the staat has no RegionNumber, so a kieskring names only its SuperiorRegionCategory."""
    tree = [
        make_region(None, RegionCategoryType.STAAT, "Nederland"),
        make_region(10, RegionCategoryType.KIESKRING, "Rotterdam", None, RegionCategoryType.STAAT),
        make_region(606, RegionCategoryType.GEMEENTE, "Schiedam", 10, RegionCategoryType.KIESKRING),
    ]
    EML110aImporter(fake_eml_file(), eml=make_eml(regions=tree)).parse()

    regions = {
        region.region_category: region for region in Region.objects.filter(election__election_config=election_config)
    }
    staat = regions[RegionCategory.STAAT]
    assert regions[RegionCategory.KIESKRING].parent == staat
    assert regions[RegionCategory.KIESKRING].csb == staat
    assert regions[RegionCategory.GEMEENTE].csb == staat


def test_leaves_parties_to_the_candidate_lists(election):
    # A blanco lijst is not a registered party, so it is never among the 110a's registered appellations
    blanco = PartyFactory(election=election, registered_name="Blanco Lijst 12", list_number=12)

    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

    assert list(Party.objects.filter(election=election)) == [blanco]


def test_creates_top_level_contest(election_config):
    EML110aImporter(fake_eml_file(), eml=make_eml(contest_id="alle")).parse()

    election = Election.objects.get(election_config=election_config)
    contest = Contest.objects.get(election=election)
    # The 110a schema omits ContestName
    assert (contest.identifier, contest.name) == ("alle", None)


def test_imports_after_the_candidate_list_of_a_single_contest_election(election_config):
    blanco = make_affiliation(12, None, [make_candidate(1, "T.E.", "Theo", "Richel")])
    EML230bImporter(fake_eml_file(), eml=make_230b_eml(affiliations=[blanco])).parse()
    election = Election.objects.get(election_config=election_config)

    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

    contest = Contest.objects.get(election=election)
    assert (contest.identifier, contest.name) == (CONTEST_ID, CONTEST_NAME)
    assert Region.objects.filter(election=election).count() == 3
    party = Party.objects.get(election=election)
    assert (party.registered_name, party.candidates.count()) == ("Blanco Lijst 12", 1)


def test_imports_after_a_candidate_list_of_a_multi_contest_election(election_config):
    EML230bImporter(fake_eml_file(), eml=make_230b_eml(contest_id="1")).parse()
    election = Election.objects.get(election_config=election_config)

    EML110aImporter(fake_eml_file(), eml=make_eml(contest_id="alle")).parse()

    assert set(Contest.objects.filter(election=election).values_list("identifier", flat=True)) == {"alle", "1"}
    assert Region.objects.filter(election=election).count() == 3


def test_correction_keeps_the_contest(election):
    original_contest_id = Contest.objects.get(election=election).pk

    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

    contest = Contest.objects.get(election=election)
    assert contest.pk == original_contest_id
    assert contest.identifier == CONTEST_ID


def test_correction_rejects_a_changed_contest(election):
    original_contest_id = Contest.objects.get(election=election).pk

    with pytest.raises(EMLImporterException, match="contest 'alle'"):
        EML110aImporter(fake_eml_file(), eml=make_eml(contest_id="alle")).parse()

    assert list(Contest.objects.filter(election=election).values_list("pk", flat=True)) == [original_contest_id]


def test_correction_keeps_the_contest_name_set_by_the_candidate_lists(election):
    Contest.objects.filter(election=election).update(name="Scheldestromen")

    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

    assert Contest.objects.get(election=election).name == "Scheldestromen"


def test_correction_keeps_regions_that_remain(election):
    original_region_ids = set(Region.objects.filter(election=election).values_list("pk", flat=True))

    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

    assert set(Region.objects.filter(election=election).values_list("pk", flat=True)) == original_region_ids


def test_correction_updates_a_changed_region(election, regions):
    gemeente = regions[RegionCategory.GEMEENTE]
    tree = [
        *ELECTION_TREE[:2],
        make_region(654, RegionCategoryType.GEMEENTE, "Borssele", 1, RegionCategoryType.KIESKRING),
    ]

    EML110aImporter(fake_eml_file(), eml=make_eml(regions=tree)).parse()

    gemeente.refresh_from_db()
    assert (gemeente.region_name, gemeente.slug) == ("Borssele", "654-borssele")
    assert gemeente.parent == regions[RegionCategory.KIESKRING]


def test_correction_deletes_regions_no_longer_in_the_tree(election):
    EML110aImporter(fake_eml_file(), eml=make_eml(regions=ELECTION_TREE[:2])).parse()

    numbers = Region.objects.filter(election=election).values_list("region_number", flat=True)
    assert set(numbers) == {"17", "1"}


def test_regions_are_matched_on_category_and_number(election_config):
    """A kieskring and a gemeente may share a region number."""
    tree = [
        make_region(17, RegionCategoryType.WATERSCHAP, "Scheldestromen"),
        make_region(1, RegionCategoryType.KIESKRING, "Scheldestromen", 17, RegionCategoryType.WATERSCHAP),
        make_region(1, RegionCategoryType.GEMEENTE, "Aa en Hunze", 1, RegionCategoryType.KIESKRING),
    ]

    EML110aImporter(fake_eml_file(), eml=make_eml(regions=tree)).parse()
    EML110aImporter(fake_eml_file(), eml=make_eml(regions=tree)).parse()

    regions = Region.objects.filter(election__election_config=election_config, region_number="1")
    assert {(region.region_category, region.region_name) for region in regions} == {
        (RegionCategory.KIESKRING, "Scheldestromen"),
        (RegionCategory.GEMEENTE, "Aa en Hunze"),
    }


def test_correction_keeps_stembureaus(election, regions):
    stembureau = RegionFactory(
        election=election,
        parent=regions[RegionCategory.GEMEENTE],
        region_category=RegionCategory.STEMBUREAU,
        region_number="0654::SB1",
    )

    EML110aImporter(fake_eml_file(), eml=make_eml()).parse()

    assert Region.objects.filter(pk=stembureau.pk).exists()


def make_110b_file(polling_places: list[tuple[int, str, str]]) -> NamedBytesIO:
    """A 110b for gemeente Borsele with (station id, name, postcode) per stembureau."""
    places = "".join(
        f'<PollingPlace Channel="polling"><PhysicalLocation><Address><Locality>'
        f"<xal:LocalityName>{name}</xal:LocalityName>"
        f"<xal:PostalCode><xal:PostalCodeNumber>{postal_code}</xal:PostalCodeNumber></xal:PostalCode>"
        f'</Locality></Address><PollingStation Id="{station_id}">1000</PollingStation></PhysicalLocation>'
        f"</PollingPlace>"
        for station_id, name, postal_code in polling_places
    )
    xml = (
        '<EML xmlns="urn:oasis:names:tc:evs:schema:eml" xmlns:xal="urn:oasis:names:tc:ciq:xsdschema:xAL:2.0" '
        'Id="110b"><ManagingAuthority><AuthorityIdentifier Id="0654">Borsele</AuthorityIdentifier>'
        f'</ManagingAuthority><ElectionEvent><Election><ElectionIdentifier Id="{ELECTION_ID}">'
        f"<ElectionName>{ELECTION_NAME}</ElectionName></ElectionIdentifier>"
        f"<Contest>{places}</Contest></Election></ElectionEvent></EML>"
    )
    return NamedBytesIO(xml.encode(), "stembureaus.eml.xml")


def test_110b_creates_stembureaus_under_the_gemeente(regions):
    gemeente = regions[RegionCategory.GEMEENTE]

    EML110bImporter(make_110b_file([(1, "Gemeentehuis ", "4451AA"), (2, "Dorpshuis", "4454 ab")])).parse()

    stembureaus = Region.objects.filter(parent=gemeente, region_category=RegionCategory.STEMBUREAU)
    assert {(sb.region_number, sb.region_name, sb.postal_code) for sb in stembureaus} == {
        ("0654::SB1", "Gemeentehuis", "4451 AA"),
        ("0654::SB2", "Dorpshuis", "4454 AB"),
    }
    assert {sb.csb for sb in stembureaus} == {gemeente.csb}
