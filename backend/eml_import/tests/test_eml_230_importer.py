"""Unit tests for EML230bImporter.

The EML input is built in code rather than parsed from a file: these tests are about
what the importer writes, not about XML. The real pyeml_bindings dataclasses are used
(not stand-ins) so that a renamed binding attribute breaks the tests instead of being
mirrored by a fake.
"""

from datetime import date

import pytest
from pyeml_bindings import (
    AffiliationIdentifierStructureKr,
    AffiliationType,
    AuthorityAddressStructure,
    AuthorityIdentifierStructureKr,
    CandidateIdentifierStructureKr,
    CandidateList,
    CandidateStructureKr,
    ContestIdentifierStructureKr,
    ElectionCategoryType,
    ElectionDate,
    ElectionIdentifierStructure230,
    ElectionSubcategory,
    ElectionSubcategoryType,
    Eml230,
    ManagingAuthorityStructureKr,
    NameLineType,
    PersonNameStructure,
    TransactionId,
)
from pyeml_bindings.x_nl_kiesraad_strict import PersonName
from xsdata.models.datatype import XmlDate

from election.models import Contest
from election.tests.factories import ElectionConfigFactory, ElectionFactory
from eml_import.utils.eml_230_importer import EML230bImporter
from party.models import Candidate, Party
from party.tests.factories import PartyFactory

ELECTION_ID = "AB2023_Scheldestromen"
CONFIG_IDENTIFIER = "AB2023"  # the part of ELECTION_ID before the "_"
ELECTION_NAME = "Algemeen bestuur van het waterschap Scheldestromen 2023"
ELECTION_SUBCATEGORY = "AB2"
ELECTION_DATE = date(2023, 3, 15)
CONTEST_ID = "geen"
CONTEST_NAME = "Scheldestromen"
REGISTERED_NAME = "CDA"
LIST_NUMBER = 1


def make_candidate(number, initials, first_name, last_name, name_prefix=None) -> CandidateStructureKr:
    """One Candidate node; the name parts sit under xNL PersonName as mixed content lists."""
    return CandidateStructureKr(
        candidate_identifier=CandidateIdentifierStructureKr(id=str(number)),
        candidate_full_name=PersonNameStructure(
            person_name=PersonName(
                name_line=NameLineType(content=[initials]),
                first_name=PersonName.FirstName(content=[first_name]) if first_name else None,
                name_prefix=PersonName.NamePrefix(content=[name_prefix]) if name_prefix else None,
                last_name=PersonName.LastName(content=[last_name]),
            )
        ),
    )


def make_affiliation(list_number, registered_name, candidates) -> CandidateList.Election.Contest.Affiliation:
    """One Affiliation; registered_name=None is the blanco lijst case."""
    return CandidateList.Election.Contest.Affiliation(
        affiliation_identifier=AffiliationIdentifierStructureKr(
            id=str(list_number),
            registered_name=registered_name,
        ),
        type_value=AffiliationType.OP_ZICHZELF_STAANDE_LIJST,
        candidate=list(candidates),
    )


# The second candidate carries a NamePrefix, the first does not.
DEFAULT_CANDIDATES = [
    make_candidate(1, "C.J.C.", "Carla", "Michielsen"),
    make_candidate(2, "L.L.", "Linda", "Giezen", name_prefix="van"),
]


def make_eml(*, affiliations=None, contest_id=CONTEST_ID) -> Eml230:
    """A 230b document. Everything the importer does not read is filled in with constants."""
    if affiliations is None:
        affiliations = [make_affiliation(LIST_NUMBER, REGISTERED_NAME, DEFAULT_CANDIDATES)]

    return Eml230(
        id="230b",
        schema_version="5",
        transaction_id=TransactionId(value="1"),
        managing_authority=ManagingAuthorityStructureKr(
            authority_identifier=AuthorityIdentifierStructureKr(id="CSB", value="Centraal stembureau"),
            authority_address=AuthorityAddressStructure(),
        ),
        issue_date=XmlDate(2023, 2, 3),
        candidate_list=CandidateList(
            election=CandidateList.Election(
                election_identifier=ElectionIdentifierStructure230(
                    id=ELECTION_ID,
                    election_name=ELECTION_NAME,
                    election_category=ElectionCategoryType.AB,
                    election_subcategory=[ElectionSubcategory(value=ElectionSubcategoryType.AB2)],
                    election_date=[ElectionDate(value=XmlDate.from_date(ELECTION_DATE))],
                ),
                contest=[
                    CandidateList.Election.Contest(
                        contest_identifier=ContestIdentifierStructureKr(id=contest_id, contest_name=CONTEST_NAME),
                        affiliation=list(affiliations),
                    )
                ],
            )
        ),
    )


@pytest.fixture
def election(db):
    """Created up front, so a Party can already exist at import time as it would after a 110a import.

    The name/subcategory match what _parse_election() resolves from ElectionIdentifier,
    so the importer's get_or_create() finds this row instead of adding a second one.
    """
    config = ElectionConfigFactory(identifier=CONFIG_IDENTIFIER)
    return ElectionFactory(
        election_config=config,
        name=ELECTION_NAME,
        subcategory=ELECTION_SUBCATEGORY,
        date=ELECTION_DATE,
    )


@pytest.fixture
def party(election):
    """The party a 110a import registered; 230b only fills in its list number."""
    return PartyFactory(election=election, registered_name=REGISTERED_NAME)


@pytest.fixture
def contest(party):
    """Import the default document; return the Contest it created."""
    EML230bImporter(make_eml(), None).parse()
    return Contest.objects.get(election=party.election)


def test_creates_contest_for_identifier(contest):
    # The name matters for PS, where the 510d importer ties a kieskring to its own contest by name
    assert (contest.identifier, contest.name) == (CONTEST_ID, CONTEST_NAME)


def test_creates_candidates_for_affiliation(contest, party):
    candidates = Candidate.objects.filter(contest=contest).order_by("identifier")

    assert [candidate.party for candidate in candidates] == [party, party]
    assert [(candidate.identifier, candidate.position) for candidate in candidates] == [(1, 1), (2, 2)]
    assert [
        (candidate.initials, candidate.first_name, candidate.name_prefix, candidate.last_name)
        for candidate in candidates
    ] == [
        ("C.J.C.", "Carla", None, "Michielsen"),
        ("L.L.", "Linda", "van", "Giezen"),
    ]


def test_assigns_list_number_to_registered_party(contest, party, election):
    party.refresh_from_db()

    assert party.list_number == LIST_NUMBER
    assert Party.objects.filter(election=election).count() == 1


def test_creates_blanco_party_for_affiliation_without_registered_name(election):
    blanco = make_affiliation(12, None, [make_candidate(1, "T.E.", "Theo", "Richel")])

    EML230bImporter(make_eml(affiliations=[blanco]), None).parse()

    party = Party.objects.get(election=election)
    assert (party.registered_name, party.list_number) == ("Blanco Lijst 12", 12)
    assert party.candidates.get().last_name == "Richel"


def test_correction_deletes_prior_contest_and_candidates(contest, party):
    EML230bImporter(make_eml(), None).parse()

    assert Contest.objects.filter(election=party.election).count() == 1
    # Correction deletes the old contest; candidates hang off the recreated one
    assert not Contest.objects.filter(pk=contest.pk).exists()
    current_contest = Contest.objects.get(election=party.election)
    assert current_contest.pk != contest.pk
    assert Candidate.objects.filter(contest=current_contest).count() == 2
    assert Candidate.objects.filter(party=party).count() == 2
