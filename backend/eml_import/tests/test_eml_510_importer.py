import re
from datetime import date

import pytest
from django.core.files.storage import default_storage
from pyeml_bindings import (
    AffiliationIdentifierStructure510,
    AuthorityAddressStructure,
    AuthorityIdentifierStructureKr,
    CandidateIdentifierStructureKr,
    CandidateStructure510,
    ContestIdentifierStructureKr,
    Count,
    CountingMethodMethodCode,
    ElectionCategoryType,
    ElectionDate,
    ElectionDomain,
    ElectionIdentifierStructure510,
    ElectionSubcategory,
    ElectionSubcategoryType,
    Eml510,
    EventIdentifier,
    ManagingAuthorityStructureKr,
    RejectedVotesType,
    RejectedVotesTypeReasonCode,
    ReportingUnitIdentifierStructureKr,
    ReportingUnitVotes,
    TransactionId,
    UncountedVotesType,
    UncountedVotesTypeReasonCode,
)
from pyeml_bindings import (
    CountingMethod as EmlCountingMethod,
)
from xsdata.models.datatype import XmlDate

from election.models import ElectionCategory, ElectionDocument, VoteCount, VoterTurnoutCount
from election.tests.factories import (
    ContestFactory,
    ElectionConfigFactory,
    ElectionDocumentFactory,
    ElectionFactory,
)
from eml_import.exceptions import EMLImporterException
from eml_import.tests.fakes import fake_eml_file
from eml_import.utils.eml_510_importer import EML510bImporter, EML510dImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import CountingMethod, RegionCategory
from mainsite.utils.eml_type import EmlType
from party.tests.factories import CandidateFactory, PartyFactory
from region.models import Region
from region.tests.factories import RegionFactory

ELECTION_DATE = date(2023, 3, 15)

WS_ELECTION_ID = "AB2023_Scheldestromen"
WS_CONFIG_IDENTIFIER = "AB2023"  # the part of the election id before the "_"
WS_ELECTION_NAME = "Algemeen bestuur van het waterschap Scheldestromen 2023"

PS_ELECTION_ID = "PS2023_Limburg"
PS_CONFIG_IDENTIFIER = "PS2023"
PS_ELECTION_NAME = "Provinciale Staten Limburg 2023"

TotalVotes = Count.Election.Contests.Contest.TotalVotes


def party_selection(selection_cls, list_number, registered_name, valid_votes):
    """A Selection introducing a party; the candidate Selections that follow belong to it.

    TotalVotes and ReportingUnitVotes have their own Selection class, hence selection_cls.
    """
    return selection_cls(
        affiliation_identifier=AffiliationIdentifierStructure510(
            id=str(list_number),
            registered_name=registered_name,
        ),
        valid_votes=valid_votes,
    )


def candidate_selection(selection_cls, valid_votes, *, number=None, short_code=None):
    """A Selection for a candidate of the party introduced above it.

    A Totaaltelling spanning several contests has no list position to refer to, so its
    candidates carry a short code and no number.
    """
    return selection_cls(
        candidate=CandidateStructure510(
            candidate_identifier=CandidateIdentifierStructureKr(
                id=str(number) if number is not None else None,
                short_code_attribute=short_code,
            )
        ),
        valid_votes=valid_votes,
    )


def rejected_votes():
    return [RejectedVotesType(value=27, reason_code=RejectedVotesTypeReasonCode.ONGELDIG)]


def uncounted_votes():
    return [UncountedVotesType(value=5, reason_code=UncountedVotesTypeReasonCode.GELDIGE_STEMPASSEN)]


def make_total_votes(selections, *, cast=100, total_counted=80, rejected=None, uncounted=None):
    return TotalVotes(
        selection=list(selections),
        cast=cast,
        total_counted=total_counted,
        rejected_votes=rejected_votes() if rejected is None else rejected,
        uncounted_votes=uncounted_votes() if uncounted is None else uncounted,
    )


def make_reporting_unit(unit_id, name, selections, *, cast=20, total_counted=18, rejected=None, uncounted=None):
    return ReportingUnitVotes(
        reporting_unit_identifier=ReportingUnitIdentifierStructureKr(id=unit_id, value=name),
        selection=list(selections),
        cast=cast,
        total_counted=total_counted,
        rejected_votes=rejected_votes() if rejected is None else rejected,
        uncounted_votes=uncounted_votes() if uncounted is None else uncounted,
    )


def make_contest(contest_id, *, total_votes=None, units=()):
    return Count.Election.Contests.Contest(
        contest_identifier=ContestIdentifierStructureKr(id=contest_id),
        total_votes=total_votes if total_votes is not None else make_total_votes([]),
        reporting_unit_votes=list(units),
    )


def make_eml(
    *,
    eml_id,
    authority_id,
    authority_name,
    contests,
    election_id=WS_ELECTION_ID,
    election_name=WS_ELECTION_NAME,
    category=ElectionCategoryType.AB,
    subcategory=ElectionSubcategoryType.AB2,
    domain=None,
    counting_method=None,
) -> Eml510:
    """A 510 document. Everything the importers do not read is filled in with constants."""
    return Eml510(
        id=eml_id,
        schema_version="5",
        transaction_id=TransactionId(value="1"),
        managing_authority=ManagingAuthorityStructureKr(
            authority_identifier=AuthorityIdentifierStructureKr(id=authority_id, value=authority_name),
            authority_address=AuthorityAddressStructure(),
        ),
        count=Count(
            counting_method=EmlCountingMethod(method_code=counting_method) if counting_method else None,
            event_identifier=EventIdentifier(),
            election=Count.Election(
                election_identifier=ElectionIdentifierStructure510(
                    id=election_id,
                    election_name=election_name,
                    election_category=category,
                    election_subcategory=[ElectionSubcategory(value=subcategory)],
                    election_domain=[domain] if domain else [],
                    election_date=[ElectionDate(value=XmlDate.from_date(ELECTION_DATE))],
                ),
                contests=Count.Election.Contests(contest=list(contests)),
            ),
        ),
    )


def make_ws_510b_eml(*, contests, authority_id="0654", authority_name="Borsele", counting_method=None):
    """A Telling published by a municipality."""
    return make_eml(
        eml_id="510b",
        authority_id=authority_id,
        authority_name=authority_name,
        contests=contests,
        counting_method=counting_method,
    )


def make_ws_510d_eml(*, contests):
    """A Totaaltelling published by a waterschap; its election domain carries a region number."""
    return make_eml(
        eml_id="510d",
        authority_id="CSB",
        authority_name="Scheldestromen",
        contests=contests,
        domain=ElectionDomain(id="17", value="Scheldestromen"),
    )


def make_ps_510d_eml(*, contests):
    """A Totaaltelling published by the provincie; in PS the election domain has no region number."""
    return make_eml(
        eml_id="510d",
        authority_id="CSB",
        authority_name="Limburg",
        contests=contests,
        election_id=PS_ELECTION_ID,
        election_name=PS_ELECTION_NAME,
        category=ElectionCategoryType.PS,
        subcategory=ElectionSubcategoryType.PS2,
        domain=ElectionDomain(value="Limburg"),
    )


@pytest.fixture
def ws_election(db):
    """Created up front, as a 110a import would have: the importers only add results to it."""
    config = ElectionConfigFactory(identifier=WS_CONFIG_IDENTIFIER, category=ElectionCategory.WS.value)
    return ElectionFactory(
        election_config=config,
        name=WS_ELECTION_NAME,
        subcategory="AB2",
        date=ELECTION_DATE,
    )


@pytest.fixture
def ws_regions(ws_election):
    """waterschap -> kieskring -> gemeente.

    The kieskring shares both number and name with the waterschap, as real ones do
    (waterschap Noorderzijlvest has a kieskring Noorderzijlvest with the same number),
    so only the region category tells the CSB from its child.
    """
    waterschap = RegionFactory(
        election=ws_election,
        region_category=RegionCategory.WATERSCHAP,
        region_number="17",
        region_name="Scheldestromen",
    )
    kieskring = RegionFactory(
        election=ws_election,
        parent=waterschap,
        csb=waterschap,
        region_category=RegionCategory.KIESKRING,
        region_number="17",
        region_name="Scheldestromen",
    )
    gemeente = RegionFactory(
        election=ws_election,
        parent=kieskring,
        csb=waterschap,
        region_category=RegionCategory.GEMEENTE,
        region_number="654",
        region_name="Borsele",
    )
    return {"waterschap": waterschap, "kieskring": kieskring, "gemeente": gemeente}


@pytest.fixture
def ws_contest(ws_election):
    return ContestFactory(election=ws_election, identifier="geen")


@pytest.fixture
def ws_parties(ws_election):
    """Keyed by list number, which is how the EML refers to them."""
    return {
        1: PartyFactory(election=ws_election, list_number=1, registered_name="Partij voor Zeeland"),
        2: PartyFactory(election=ws_election, list_number=2, registered_name="CDA"),
    }


@pytest.fixture
def ws_candidates(ws_contest, ws_parties):
    """Keyed by (list number, position on that list)."""
    return {
        (list_number, position): CandidateFactory(
            contest=ws_contest,
            party=party,
            identifier=position,
            position=position,
            last_name=f"Kandidaat {list_number}-{position}",
        )
        for list_number, party in ws_parties.items()
        for position in (1, 2)
    }


@pytest.fixture
def ws_importer(ws_election):
    """A Telling importer, for exercising the base class helpers directly."""
    return EML510bImporter(make_ws_510b_eml(contests=[]), fake_eml_file())


@pytest.fixture
def ws_csb_importer(ws_election):
    """A Totaaltelling importer, for exercising the base class helpers directly."""
    return EML510dImporter(make_ws_510d_eml(contests=[]), fake_eml_file())


@pytest.mark.parametrize(
    ("method_code", "expected"),
    [
        (CountingMethodMethodCode.CENTRALE_STEMOPNEMING, CountingMethod.CSO),
        (CountingMethodMethodCode.DECENTRALE_STEMOPNEMING, CountingMethod.DSO),
        (None, None),
    ],
)
def test_counting_method(method_code, expected):
    count = make_ws_510b_eml(contests=[], counting_method=method_code).count

    assert EML510bImporter._counting_method(count) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Nutsgebouw Zwammerdam", "Nutsgebouw Zwammerdam"),
        ("Heinkenszand, De Stenge (postcode: 4451 CZ)", "Heinkenszand, De Stenge"),
        ("Stembureau Nutsgebouw Zwammerdam", "Nutsgebouw Zwammerdam"),
        ("Stembureau Stembureau Nutsgebouw Zwammerdam", "Nutsgebouw Zwammerdam"),
    ],
)
def test_polling_station_name(name, expected):
    unit = make_reporting_unit("0654::SB1", name, [])

    assert EML510bImporter._polling_station_name(unit) == expected


def test_parse_party_candidate_votecounts_builds_party_and_candidate_rows(
    ws_importer, ws_regions, ws_contest, ws_parties, ws_candidates
):
    party, candidate = ws_parties[1], ws_candidates[(1, 1)]
    items = [
        party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 100),
        candidate_selection(TotalVotes.Selection, 60, number=1),
    ]
    vote_counts: list[VoteCount] = []

    ws_importer._parse_party_candidate_votecounts(
        ws_contest, ws_regions["gemeente"], items, {1: party}, {(party.id, 1): candidate}, vote_counts
    )

    assert len(vote_counts) == 2
    party_row, candidate_row = vote_counts
    assert party_row.result_level == VoteCount.RESULT_LEVEL_PARTY
    assert party_row.party == party
    assert party_row.candidate is None
    assert party_row.valid_votes == 100
    assert party_row.eml_type == EmlType.EML_510b
    assert candidate_row.result_level == VoteCount.RESULT_LEVEL_CANDIDATE
    assert candidate_row.party == party
    assert candidate_row.candidate == candidate
    assert candidate_row.valid_votes == 60


def test_parse_party_candidate_votecounts_raises_for_unknown_candidate(ws_importer, ws_regions, ws_contest, ws_parties):
    party = ws_parties[1]
    items = [
        party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 100),
        candidate_selection(TotalVotes.Selection, 5, number=999),
    ]
    vote_counts: list[VoteCount] = []

    with pytest.raises(
        EMLImporterException,
        match="Candidate 999 not found within party Partij voor Zeeland",
    ):
        ws_importer._parse_party_candidate_votecounts(
            ws_contest, ws_regions["gemeente"], items, {1: party}, {}, vote_counts
        )

    assert len(vote_counts) == 1


def test_parse_party_candidate_votecounts_records_short_code_mapping(
    ws_importer, ws_regions, ws_contest, ws_parties, ws_candidates
):
    """A Totaaltelling learns the short codes from the reporting units it reads first."""
    party, candidate = ws_parties[1], ws_candidates[(1, 1)]
    items = [
        party_selection(ReportingUnitVotes.Selection, 1, "Partij voor Zeeland", 100),
        candidate_selection(ReportingUnitVotes.Selection, 60, number=1, short_code="TheunsMLM"),
    ]
    candidate_by_short_code: dict[tuple[int, str], int] = {}

    ws_importer._parse_party_candidate_votecounts(
        ws_contest,
        ws_regions["gemeente"],
        items,
        {1: party},
        {(party.id, 1): candidate},
        [],
        candidate_by_short_code=candidate_by_short_code,
    )

    assert candidate_by_short_code == {(party.id, "TheunsMLM"): candidate.id}


def test_parse_party_candidate_votecounts_resolves_candidate_by_short_code(
    ws_importer, ws_regions, ws_contest, ws_parties, ws_candidates
):
    """Totals spanning several contests carry a short code instead of a list position."""
    party, candidate = ws_parties[1], ws_candidates[(1, 1)]
    items = [
        party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 100),
        candidate_selection(TotalVotes.Selection, 60, short_code="TheunsMLM"),
    ]
    vote_counts: list[VoteCount] = []

    ws_importer._parse_party_candidate_votecounts(
        ws_contest,
        ws_regions["gemeente"],
        items,
        {1: party},
        {(None, candidate.id): candidate},
        vote_counts,
        candidate_by_short_code={(party.id, "TheunsMLM"): candidate.id},
    )

    assert [row.candidate for row in vote_counts] == [None, candidate]


def test_parse_party_candidate_votecounts_raises_for_unknown_short_code(
    ws_importer, ws_regions, ws_contest, ws_parties
):
    party = ws_parties[1]
    items = [
        party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 100),
        candidate_selection(TotalVotes.Selection, 60, short_code="Onbekend"),
    ]
    vote_counts: list[VoteCount] = []

    with pytest.raises(
        EMLImporterException,
        match="Candidate Onbekend not found within party Partij voor Zeeland",
    ):
        ws_importer._parse_party_candidate_votecounts(
            ws_contest,
            ws_regions["gemeente"],
            items,
            {1: party},
            {},
            vote_counts,
            candidate_by_short_code={},
        )

    assert len(vote_counts) == 1
    assert vote_counts[0].result_level == VoteCount.RESULT_LEVEL_PARTY


def test_collect_turnout_counts_builds_rejected_uncounted_and_total_rows(ws_csb_importer, ws_regions, ws_contest):
    votes = make_reporting_unit(
        "0654",
        "Borsele",
        [],
        cast=100,
        total_counted=80,
        rejected=[RejectedVotesType(value=27, reason_code=RejectedVotesTypeReasonCode.ONGELDIG)],
        uncounted=[UncountedVotesType(value=5, reason_code=UncountedVotesTypeReasonCode.GELDIGE_STEMPASSEN)],
    )
    turnout_counts: list[VoterTurnoutCount] = []

    ws_csb_importer._collect_turnout_counts(ws_contest, ws_regions["gemeente"], votes, turnout_counts)

    assert [(row.category, row.reason_code, row.votes) for row in turnout_counts] == [
        (VoterTurnoutCount.CATEGORY_REJECTED, "ongeldig", 27),
        (VoterTurnoutCount.CATEGORY_UNCOUNTED, "geldige stempassen", 5),
        (VoterTurnoutCount.CATEGORY_TOTALS, "total counted", 80),
    ]
    assert all(row.eml_type == EmlType.EML_510d for row in turnout_counts)


def make_polling_station_document(*names_by_id):
    return make_ws_510b_eml(
        contests=[make_contest("geen", units=[make_reporting_unit(unit_id, name, []) for unit_id, name in names_by_id])]
    )


def test_ensure_polling_stations_creates_missing_stations(ws_regions):
    eml = make_polling_station_document(("0654::SB1", "Stembureau A"), ("0654::SB2", "Stembureau B"))
    importer = EML510bImporter(eml, fake_eml_file())

    stations = importer._ensure_polling_stations(ws_regions["gemeente"])

    assert set(stations.keys()) == {("0654::SB1", "A"), ("0654::SB2", "B")}
    created = Region.objects.filter(parent=ws_regions["gemeente"], region_category=RegionCategory.STEMBUREAU)
    assert created.count() == 2
    # The polling stations hang off the gemeente, but their CSB is the election-tree root
    assert all(station.csb == ws_regions["waterschap"] for station in created)


def test_ensure_polling_stations_reuses_existing_stations(ws_regions):
    existing = RegionFactory(
        election=ws_regions["gemeente"].election,
        parent=ws_regions["gemeente"],
        region_category=RegionCategory.STEMBUREAU,
        region_number="0654::SB1",
        region_name="A",
    )
    eml = make_polling_station_document(("0654::SB1", "Stembureau A"), ("0654::SB2", "Stembureau B"))
    importer = EML510bImporter(eml, fake_eml_file())

    stations = importer._ensure_polling_stations(ws_regions["gemeente"])

    assert stations[("0654::SB1", "A")] == existing
    assert Region.objects.filter(parent=ws_regions["gemeente"], region_category=RegionCategory.STEMBUREAU).count() == 2


STORAGE_KEY_TIMESTAMP = r"\d{8}T\d{12}"


def make_ws_importer(importer_cls, eml_file):
    """A real importer for the waterschap election, whichever 510 flavour is under test."""
    eml = make_ws_510b_eml(contests=[]) if importer_cls is EML510bImporter else make_ws_510d_eml(contests=[])
    return importer_cls(eml, eml_file)


def assert_storage_key(storage_key: str, expected_stem: str) -> None:
    """storage_key is {election}/{stem}_{timestamp}.eml.xml after corrections."""
    assert re.fullmatch(rf"{re.escape(expected_stem)}_{STORAGE_KEY_TIMESTAMP}\.eml\.xml", storage_key)


@pytest.mark.parametrize("importer_cls", [EML510bImporter, EML510dImporter])
def test_store_eml_saves_path_input_and_creates_document(importer_cls, ws_regions, tmp_path):
    content = b"<eml>counted votes</eml>"
    xml_path = tmp_path / "input.eml.xml"
    xml_path.write_bytes(content)
    importer = make_ws_importer(importer_cls, xml_path)

    importer._store_eml(ws_regions["gemeente"])

    doc = ElectionDocument.objects.get()
    assert default_storage.open(doc.storage_key).read() == content
    assert doc.region == ws_regions["gemeente"]
    assert doc.content_type == "application/xml"
    assert doc.file_type == importer.eml_type
    assert doc.size == len(content)


def test_store_eml_saves_named_bytes_io_input(ws_regions):
    """Regression test: NamedBytesIO has no .stat(), unlike Path."""
    content = b"<eml>counted votes from github</eml>"
    importer = make_ws_importer(EML510bImporter, NamedBytesIO(content, "input.eml.xml"))

    importer._store_eml(ws_regions["gemeente"])

    doc = ElectionDocument.objects.get()
    assert default_storage.open(doc.storage_key).read() == content
    assert doc.size == len(content)


@pytest.mark.parametrize(
    ("importer_cls", "expected_label"),
    [(EML510bImporter, "Telling_GSB"), (EML510dImporter, "Totaaltelling_CSB")],
)
def test_store_eml_filename_without_parent(importer_cls, expected_label, ws_regions):
    importer = make_ws_importer(importer_cls, NamedBytesIO(b"<eml/>", "x.xml"))

    importer._store_eml(ws_regions["waterschap"])

    doc = ElectionDocument.objects.get()
    assert_storage_key(doc.storage_key, f"AB2023/AB2023_{expected_label}_17_Scheldestromen")


def test_store_eml_filename_with_parent_sanitizes_special_characters(ws_election):
    parent = RegionFactory(election=ws_election, region_number="1", region_name="Scheldestromen (Test)")
    region = RegionFactory(
        election=ws_election,
        parent=parent,
        region_number="654",
        region_name="'s-Gravenhage/Voorburg",
    )
    importer = make_ws_importer(EML510bImporter, NamedBytesIO(b"<eml/>", "x.xml"))

    importer._store_eml(region)

    doc = ElectionDocument.objects.get()
    assert_storage_key(
        doc.storage_key,
        "AB2023/AB2023_Telling_GSB_1_Scheldestromen_Test_654_s-GravenhageVoorburg",
    )


def test_store_eml_archives_existing_document_on_reimport(ws_regions):
    """Corrections archive the previous current document, then store a new one."""
    existing = ElectionDocumentFactory(
        storage_key="AB2023/AB2023_Telling_GSB_17_Scheldestromen.eml.xml",
        region=ws_regions["waterschap"],
        content_type="application/xml",
        file_type=EmlType.EML_510b,
        size=1,
    )
    content = b"<eml>corrected counts, longer than before</eml>"
    importer = make_ws_importer(EML510bImporter, NamedBytesIO(content, "x.xml"))

    importer._archive(ws_regions["waterschap"])
    importer._store_eml(ws_regions["waterschap"])

    existing.refresh_from_db()
    assert existing.is_current is False
    assert ElectionDocument.objects.filter(region=ws_regions["waterschap"]).count() == 1
    doc = ElectionDocument.objects.get(region=ws_regions["waterschap"])
    assert doc.pk != existing.pk
    assert doc.size == len(content)
    assert default_storage.open(doc.storage_key).read() == content
    assert_storage_key(doc.storage_key, "AB2023/AB2023_Telling_GSB_17_Scheldestromen")


def make_ws_telling(*, authority_id="0654", authority_name="Borsele", counting_method=None):
    """The Telling of gemeente Borsele: totals plus the votes of one polling station."""
    totals = make_total_votes(
        [
            party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 1779),
            candidate_selection(TotalVotes.Selection, 1107, number=1),
        ]
    )
    unit = make_reporting_unit(
        "0654::SB1",
        "Stembureau Heinkenszand, De Stenge (postcode: 4451 CZ)",
        [
            party_selection(ReportingUnitVotes.Selection, 1, "Partij voor Zeeland", 200),
            candidate_selection(ReportingUnitVotes.Selection, 120, number=1),
        ],
    )
    return make_ws_510b_eml(
        contests=[make_contest("geen", total_votes=totals, units=[unit])],
        authority_id=authority_id,
        authority_name=authority_name,
        counting_method=counting_method,
    )


def test_510b_imports_votes_for_gsb_and_polling_stations(ws_regions, ws_contest, ws_parties, ws_candidates):
    EML510bImporter(make_ws_telling(), fake_eml_file()).parse()

    station = Region.objects.get(region_category=RegionCategory.STEMBUREAU)
    assert (station.parent, station.csb, station.region_name) == (
        ws_regions["gemeente"],
        ws_regions["waterschap"],
        "Heinkenszand, De Stenge",
    )
    party, candidate = ws_parties[1], ws_candidates[(1, 1)]
    assert [
        (row.region, row.result_level, row.party, row.candidate, row.valid_votes)
        for row in VoteCount.objects.order_by("valid_votes")
    ] == [
        (station, VoteCount.RESULT_LEVEL_CANDIDATE, party, candidate, 120),
        (station, VoteCount.RESULT_LEVEL_PARTY, party, None, 200),
        (ws_regions["gemeente"], VoteCount.RESULT_LEVEL_CANDIDATE, party, candidate, 1107),
        (ws_regions["gemeente"], VoteCount.RESULT_LEVEL_PARTY, party, None, 1779),
    ]
    # Turnout is collected for the gemeente and for each polling station
    assert VoterTurnoutCount.objects.filter(region=ws_regions["gemeente"]).count() == 3
    assert VoterTurnoutCount.objects.filter(region=station).count() == 3


def test_510b_correction_replaces_municipality_tree(ws_regions, ws_contest, ws_parties, ws_candidates):
    """A second telling for the same gemeente tosses stembureaus and 510b counts, then reimports."""
    EML510bImporter(make_ws_telling(), fake_eml_file()).parse()
    original_station_id = Region.objects.get(region_category=RegionCategory.STEMBUREAU).pk

    totals = make_total_votes(
        [
            party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 1800),
            candidate_selection(TotalVotes.Selection, 1200, number=1),
        ]
    )
    unit = make_reporting_unit(
        "0654::SB2",
        "Stembureau Ander Bureau (postcode: 4451 AA)",
        [
            party_selection(ReportingUnitVotes.Selection, 1, "Partij voor Zeeland", 50),
            candidate_selection(ReportingUnitVotes.Selection, 40, number=1),
        ],
    )
    correction = make_ws_510b_eml(contests=[make_contest("geen", total_votes=totals, units=[unit])])

    EML510bImporter(correction, fake_eml_file()).parse()

    gemeente = ws_regions["gemeente"]
    assert Region.objects.filter(pk=gemeente.pk).exists()
    assert not Region.objects.filter(pk=original_station_id).exists()

    stations = list(Region.objects.filter(parent=gemeente, region_category=RegionCategory.STEMBUREAU))
    assert len(stations) == 1
    assert stations[0].region_name == "Ander Bureau"

    party, candidate = ws_parties[1], ws_candidates[(1, 1)]
    assert [
        (row.region, row.result_level, row.party, row.candidate, row.valid_votes)
        for row in VoteCount.objects.filter(eml_type=EmlType.EML_510b).order_by("valid_votes")
    ] == [
        (stations[0], VoteCount.RESULT_LEVEL_CANDIDATE, party, candidate, 40),
        (stations[0], VoteCount.RESULT_LEVEL_PARTY, party, None, 50),
        (gemeente, VoteCount.RESULT_LEVEL_CANDIDATE, party, candidate, 1200),
        (gemeente, VoteCount.RESULT_LEVEL_PARTY, party, None, 1800),
    ]


def test_510b_marks_region_as_counted_and_stores_document(ws_regions, ws_contest, ws_parties, ws_candidates):
    eml = make_ws_telling(counting_method=CountingMethodMethodCode.DECENTRALE_STEMOPNEMING)

    EML510bImporter(eml, NamedBytesIO(b"<eml/>", "telling.eml.xml")).parse()

    gemeente = ws_regions["gemeente"]
    gemeente.refresh_from_db()
    assert gemeente.results_available_at is not None
    assert gemeente.counting_method == CountingMethod.DSO
    doc = ElectionDocument.objects.get()
    assert doc.region == gemeente
    assert_storage_key(doc.storage_key, "AB2023/AB2023_Telling_GSB_17_Scheldestromen_654_Borsele")


def test_510b_rejects_region_outside_the_election(ws_regions, ws_contest, ws_parties, ws_candidates):
    """A gemeente that the election definition does not mention cannot be imported."""
    eml = make_ws_telling(authority_id="0999", authority_name="Onbekend")

    with pytest.raises(
        EMLImporterException,
        match=r"Municipality Onbekend 999 does not exist in the election definition of election .*",
    ):
        EML510bImporter(eml, NamedBytesIO(b"<eml/>", "telling.eml.xml")).parse()

    assert not VoteCount.objects.exists()
    assert not VoterTurnoutCount.objects.exists()
    assert not ElectionDocument.objects.exists()
    assert not Region.objects.filter(region_category=RegionCategory.STEMBUREAU).exists()


@pytest.fixture
def ws_totaaltelling(ws_regions, ws_contest, ws_parties, ws_candidates):
    """Import the waterschap Totaaltelling: totals plus a breakdown for gemeente Borsele."""
    totals = make_total_votes(
        [
            party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 24949),
            candidate_selection(TotalVotes.Selection, 10890, number=1),
        ]
    )
    unit = make_reporting_unit(
        "0654",
        "Borsele",
        [
            party_selection(ReportingUnitVotes.Selection, 1, "Partij voor Zeeland", 1779),
            candidate_selection(ReportingUnitVotes.Selection, 1107, number=1),
        ],
    )
    EML510dImporter(
        make_ws_510d_eml(contests=[make_contest("geen", total_votes=totals, units=[unit])]), fake_eml_file()
    ).parse()


def test_510d_resolves_csb_region_from_election_category(ws_totaaltelling, ws_regions):
    """The CSB of a waterschapsverkiezing is the waterschap, not its identically named kieskring."""
    totals = VoteCount.objects.get(result_level=VoteCount.RESULT_LEVEL_PARTY, valid_votes=24949)

    assert totals.region == ws_regions["waterschap"]
    assert not VoteCount.objects.filter(region=ws_regions["kieskring"]).exists()


def test_510d_breaks_down_per_gemeente_when_csb_has_one_child(ws_totaaltelling, ws_regions, ws_parties, ws_candidates):
    rows = VoteCount.objects.filter(region=ws_regions["gemeente"]).order_by("valid_votes")

    assert [(row.result_level, row.party, row.candidate, row.valid_votes) for row in rows] == [
        (VoteCount.RESULT_LEVEL_CANDIDATE, ws_parties[1], ws_candidates[(1, 1)], 1107),
        (VoteCount.RESULT_LEVEL_PARTY, ws_parties[1], None, 1779),
    ]


def test_510d_correction_deletes_csb_and_descendant_counts(ws_regions, ws_contest, ws_parties, ws_candidates):
    """A second Totaaltelling for the same CSB deletes prior counts and archives the EML document."""
    totals = make_total_votes(
        [
            party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 24949),
            candidate_selection(TotalVotes.Selection, 10890, number=1),
        ]
    )
    unit = make_reporting_unit(
        "0654",
        "Borsele",
        [
            party_selection(ReportingUnitVotes.Selection, 1, "Partij voor Zeeland", 1779),
            candidate_selection(ReportingUnitVotes.Selection, 1107, number=1),
        ],
    )
    first = make_ws_510d_eml(contests=[make_contest("geen", total_votes=totals, units=[unit])])
    EML510dImporter(first, NamedBytesIO(b"<eml>first</eml>", "totaal.eml.xml")).parse()

    original_count_ids = set(VoteCount.objects.filter(eml_type=EmlType.EML_510d).values_list("pk", flat=True))
    original_turnout_ids = set(VoterTurnoutCount.objects.filter(eml_type=EmlType.EML_510d).values_list("pk", flat=True))
    original_doc = ElectionDocument.objects.get(region=ws_regions["waterschap"])

    corrected_totals = make_total_votes(
        [
            party_selection(TotalVotes.Selection, 1, "Partij voor Zeeland", 25000),
            candidate_selection(TotalVotes.Selection, 11000, number=1),
        ]
    )
    corrected_unit = make_reporting_unit(
        "0654",
        "Borsele",
        [
            party_selection(ReportingUnitVotes.Selection, 1, "Partij voor Zeeland", 1800),
            candidate_selection(ReportingUnitVotes.Selection, 1200, number=1),
        ],
    )
    correction = make_ws_510d_eml(contests=[make_contest("geen", total_votes=corrected_totals, units=[corrected_unit])])
    EML510dImporter(correction, NamedBytesIO(b"<eml>corrected</eml>", "totaal.eml.xml")).parse()

    waterschap = ws_regions["waterschap"]
    gemeente = ws_regions["gemeente"]
    party, candidate = ws_parties[1], ws_candidates[(1, 1)]

    assert not VoteCount.objects.filter(pk__in=original_count_ids).exists()
    assert not VoterTurnoutCount.objects.filter(pk__in=original_turnout_ids).exists()

    assert [
        (row.region, row.result_level, row.party, row.candidate, row.valid_votes)
        for row in VoteCount.objects.filter(eml_type=EmlType.EML_510d).order_by("valid_votes")
    ] == [
        (gemeente, VoteCount.RESULT_LEVEL_CANDIDATE, party, candidate, 1200),
        (gemeente, VoteCount.RESULT_LEVEL_PARTY, party, None, 1800),
        (waterschap, VoteCount.RESULT_LEVEL_CANDIDATE, party, candidate, 11000),
        (waterschap, VoteCount.RESULT_LEVEL_PARTY, party, None, 25000),
    ]

    original_doc.refresh_from_db()
    assert original_doc.is_current is False
    doc = ElectionDocument.objects.get(region=waterschap)
    assert doc.pk != original_doc.pk
    assert default_storage.open(doc.storage_key).read() == b"<eml>corrected</eml>"


@pytest.fixture
def ps_election(db):
    config = ElectionConfigFactory(identifier=PS_CONFIG_IDENTIFIER, category=ElectionCategory.PS.value)
    return ElectionFactory(
        election_config=config,
        name=PS_ELECTION_NAME,
        subcategory="PS2",
        date=ELECTION_DATE,
    )


@pytest.fixture
def ps_regions(ps_election):
    """provincie -> two kieskringen, so the Totaaltelling breaks down per kieskring."""
    provincie = RegionFactory(
        election=ps_election,
        region_category=RegionCategory.PROVINCIE,
        region_number="12",
        region_name="Limburg",
    )
    kieskringen = {
        name: RegionFactory(
            election=ps_election,
            parent=provincie,
            csb=provincie,
            region_category=RegionCategory.KIESKRING,
            region_number=str(number),
            region_name=name,
        )
        for number, name in enumerate(("Maastricht", "Venlo"), start=1)
    }
    return {"provincie": provincie, **kieskringen}


@pytest.fixture
def ps_contests(ps_election):
    """The contest the 110a defines, plus the per-kieskring contests the 230b files add."""
    return {
        "alle": ContestFactory(election=ps_election, identifier="alle"),
        "Maastricht": ContestFactory(election=ps_election, identifier="I", name="Maastricht"),
        "Venlo": ContestFactory(election=ps_election, identifier="II", name="Venlo"),
    }


@pytest.fixture
def ps_candidates(ps_election, ps_contests):
    """The same party fields a different list in each kieskring, both at position 1."""
    party = PartyFactory(election=ps_election, list_number=1, registered_name="CDA")
    return {
        name: CandidateFactory(contest=ps_contests[name], party=party, identifier=1, position=1, last_name=name)
        for name in ("Maastricht", "Venlo")
    }


@pytest.fixture
def ps_totaaltelling(ps_regions, ps_contests, ps_candidates):
    """Import the Limburg Totaaltelling.

    Its single contest is "alle": the candidates belong to a contest per kieskring, and the
    provincie-wide totals refer to them by short code only.
    """
    units = [
        make_reporting_unit(
            "HSB1",
            "Kieskring Maastricht",
            [
                party_selection(ReportingUnitVotes.Selection, 1, "CDA", 21252),
                candidate_selection(ReportingUnitVotes.Selection, 5992, number=1, short_code="TheunsMLM"),
            ],
        ),
        make_reporting_unit(
            "HSB2",
            "Kieskring Venlo",
            [
                party_selection(ReportingUnitVotes.Selection, 1, "CDA", 22067),
                candidate_selection(ReportingUnitVotes.Selection, 4414, number=1, short_code="BrugmanJEM"),
            ],
        ),
    ]
    totals = make_total_votes(
        [
            party_selection(TotalVotes.Selection, 1, "CDA", 43319),
            candidate_selection(TotalVotes.Selection, 10406, short_code="TheunsMLM"),
            candidate_selection(TotalVotes.Selection, 8262, short_code="BrugmanJEM"),
        ]
    )
    EML510dImporter(
        make_ps_510d_eml(contests=[make_contest("alle", total_votes=totals, units=units)]), fake_eml_file()
    ).parse()


def test_510d_breaks_down_per_kieskring_when_csb_has_multiple_children(ps_totaaltelling, ps_regions):
    """Reporting unit "Kieskring Maastricht" is the kieskring named Maastricht.

    Also covers the PS election domain, which carries no region number for the CSB to be found by.
    """
    rows = VoteCount.objects.filter(result_level=VoteCount.RESULT_LEVEL_PARTY).order_by("valid_votes")

    assert [(row.region, row.valid_votes) for row in rows] == [
        (ps_regions["Maastricht"], 21252),
        (ps_regions["Venlo"], 22067),
        (ps_regions["provincie"], 43319),
    ]


def test_510d_uses_contest_per_child_region_when_contest_is_alle(ps_totaaltelling, ps_regions):
    def contest_identifiers(region):
        return set(VoteCount.objects.filter(region=region).values_list("contest__identifier", flat=True))

    assert contest_identifiers(ps_regions["Maastricht"]) == {"I"}
    assert contest_identifiers(ps_regions["Venlo"]) == {"II"}
    assert contest_identifiers(ps_regions["provincie"]) == {"alle"}


def test_510d_resolves_total_candidate_votes_by_short_code(ps_totaaltelling, ps_regions, ps_candidates):
    """The totals name no list position, so the candidates are looked up by the short codes
    collected while reading the kieskringen -- across contests."""
    rows = VoteCount.objects.filter(
        region=ps_regions["provincie"],
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
    ).order_by("valid_votes")

    assert [(row.candidate, row.valid_votes) for row in rows] == [
        (ps_candidates["Venlo"], 8262),
        (ps_candidates["Maastricht"], 10406),
    ]
