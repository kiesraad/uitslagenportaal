import logging
from types import SimpleNamespace

import pytest
from django.core.files.storage import default_storage
from pyeml_bindings import CountingMethodMethodCode

from election.models import ElectionDocument, VoteCount, VoterTurnoutCount
from election.tests.factories import ContestFactory, ElectionConfigFactory, ElectionDocumentFactory
from eml_import.exceptions import EMLImporterException
from eml_import.utils.eml_510_importer import EML510bImporter, EML510dImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import CountingMethod, RegionCategory
from mainsite.utils.eml_type import EmlType
from party.tests.factories import CandidateFactory, PartyFactory
from region.models import Region
from region.tests.factories import RegionFactory


def make_importer[T](importer_cls: type[T], *, election_config=None, election=None, eml=None, eml_file=None) -> T:
    """Build an importer instance without running __init__/_parse_election.

    _store_eml and the helper methods below only touch election_config, election,
    eml_type (a class attribute) and eml_file/eml -- not the full parsed EML tree
    that __init__ normally requires to resolve election_config from the file.
    """
    importer = object.__new__(importer_cls)
    importer.election_config = election_config
    importer.election = election
    importer.eml = eml
    importer.eml_file = eml_file
    importer.logger = logging.getLogger(f"test.{importer_cls.__name__}")
    return importer


# --- _counting_method (static, pure) -----------------------------------------------------------


@pytest.mark.parametrize(
    ("counting_method", "expected"),
    [
        (SimpleNamespace(method_code=CountingMethodMethodCode.CENTRALE_STEMOPNEMING), CountingMethod.CSO),
        (SimpleNamespace(method_code=CountingMethodMethodCode.DECENTRALE_STEMOPNEMING), CountingMethod.DSO),
        (None, None),
    ],
)
def test_counting_method(counting_method, expected):
    count = SimpleNamespace(counting_method=counting_method)

    assert EML510bImporter._counting_method(count) == expected


def test_counting_method_missing_attribute_returns_none():
    assert EML510bImporter._counting_method(SimpleNamespace()) is None


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
    unit = SimpleNamespace(reporting_unit_identifier=SimpleNamespace(value=name))

    assert EML510bImporter._polling_station_name(unit) == expected


@pytest.mark.django_db
def test_parse_party_candidate_votecounts_builds_party_and_candidate_rows():
    contest = ContestFactory()
    region = RegionFactory(election=contest.election)
    party = PartyFactory(election=contest.election, list_number=1)
    candidate = CandidateFactory(contest=contest, party=party, identifier=1)
    items = [
        SimpleNamespace(affiliation_identifier=SimpleNamespace(id="1"), valid_votes=100, candidate=None),
        SimpleNamespace(
            affiliation_identifier=None,
            valid_votes=60,
            candidate=SimpleNamespace(candidate_identifier=SimpleNamespace(id="1")),
        ),
    ]
    importer = make_importer(EML510bImporter)
    vote_counts: list[VoteCount] = []

    importer._parse_party_candidate_votecounts(
        contest, region, items, {1: party}, {(party.id, 1): candidate}, vote_counts
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


@pytest.mark.django_db
def test_parse_party_candidate_votecounts_raises_for_unknown_candidate():
    contest = ContestFactory()
    region = RegionFactory(election=contest.election)
    party = PartyFactory(election=contest.election, list_number=1, registered_name="Test Party")
    items = [
        SimpleNamespace(affiliation_identifier=SimpleNamespace(id="1"), valid_votes=100, candidate=None),
        SimpleNamespace(
            affiliation_identifier=None,
            valid_votes=5,
            candidate=SimpleNamespace(candidate_identifier=SimpleNamespace(id="999")),
        ),
    ]
    importer = make_importer(EML510bImporter)
    vote_counts: list[VoteCount] = []

    with pytest.raises(
        EMLImporterException,
        match="Candidate 999 not found within party Test Party",
    ):
        importer._parse_party_candidate_votecounts(contest, region, items, {1: party}, {}, vote_counts)

    assert len(vote_counts) == 1
    assert vote_counts[0].result_level == VoteCount.RESULT_LEVEL_PARTY


@pytest.mark.django_db
def test_collect_turnout_counts_builds_rejected_uncounted_and_total_rows():
    contest = ContestFactory()
    region = RegionFactory(election=contest.election)
    votes = SimpleNamespace(
        rejected_votes=[SimpleNamespace(reason_code=SimpleNamespace(value="ongeldig"), value=27)],
        uncounted_votes=[SimpleNamespace(reason_code=SimpleNamespace(value="blanco"), value=5)],
        cast=100,
        total_counted=80,
    )
    importer = make_importer(EML510dImporter)
    turnout_counts: list[VoterTurnoutCount] = []

    importer._collect_turnout_counts(contest, region, votes, turnout_counts)

    assert len(turnout_counts) == 4
    rejected, uncounted, cast, total_counted = turnout_counts
    assert (rejected.category, rejected.reason_code, rejected.votes) == (
        VoterTurnoutCount.CATEGORY_REJECTED,
        "ongeldig",
        27,
    )
    assert (uncounted.category, uncounted.reason_code, uncounted.votes) == (
        VoterTurnoutCount.CATEGORY_UNCOUNTED,
        "blanco",
        5,
    )
    assert (cast.category, cast.reason_code, cast.votes) == (VoterTurnoutCount.CATEGORY_TOTALS, "cast", 100)
    assert (total_counted.category, total_counted.reason_code, total_counted.votes) == (
        VoterTurnoutCount.CATEGORY_TOTALS,
        "total counted",
        80,
    )
    assert all(row.eml_type == EmlType.EML_510d for row in turnout_counts)


def _reporting_unit(number, name):
    return SimpleNamespace(reporting_unit_identifier=SimpleNamespace(id=number, value=name))


def _fake_eml_with_reporting_units(units):
    return SimpleNamespace(
        count=SimpleNamespace(
            election=SimpleNamespace(contests=SimpleNamespace(contest=[SimpleNamespace(reporting_unit_votes=units)]))
        )
    )


@pytest.mark.django_db
def test_ensure_polling_stations_creates_missing_stations():
    region = RegionFactory()
    units = [_reporting_unit("0654::SB1", "Stembureau A"), _reporting_unit("0654::SB2", "Stembureau B")]
    importer = make_importer(EML510bImporter, election=region.election, eml=_fake_eml_with_reporting_units(units))

    stations = importer._ensure_polling_stations(region)

    assert set(stations.keys()) == {("0654::SB1", "A"), ("0654::SB2", "B")}
    created = Region.objects.filter(parent=region, region_category=RegionCategory.STEMBUREAU)
    assert created.count() == 2
    assert all(station.csb == region for station in created)


@pytest.mark.django_db
def test_ensure_polling_stations_reuses_existing_stations():
    region = RegionFactory()
    existing = RegionFactory(
        election=region.election,
        parent=region,
        region_category=RegionCategory.STEMBUREAU,
        region_number="0654::SB1",
        region_name="A",
    )
    units = [_reporting_unit("0654::SB1", "Stembureau A"), _reporting_unit("0654::SB2", "Stembureau B")]
    importer = make_importer(EML510bImporter, election=region.election, eml=_fake_eml_with_reporting_units(units))

    stations = importer._ensure_polling_stations(region)

    assert stations[("0654::SB1", "A")] == existing
    assert Region.objects.filter(parent=region, region_category=RegionCategory.STEMBUREAU).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("importer_cls", [EML510bImporter, EML510dImporter])
def test_store_eml_saves_path_input_and_creates_document(importer_cls, tmp_path):
    election_config = ElectionConfigFactory(identifier="AB2023")
    region = RegionFactory(region_number="654", region_name="Borsele")
    content = b"<eml>counted votes</eml>"
    xml_path = tmp_path / "input.eml.xml"
    xml_path.write_bytes(content)
    importer = make_importer(importer_cls, election_config=election_config, eml_file=xml_path)

    importer._store_eml(region)

    doc = ElectionDocument.objects.get()
    assert default_storage.open(doc.storage_key).read() == content
    assert doc.region == region
    assert doc.content_type == "application/xml"
    assert doc.file_type == ElectionDocument.FileType.EML510B
    assert doc.size == len(content)


@pytest.mark.django_db
def test_store_eml_saves_named_bytes_io_input(tmp_path):
    """Regression test: NamedBytesIO has no .stat(), unlike Path."""
    election_config = ElectionConfigFactory(identifier="AB2023")
    region = RegionFactory(region_number="654", region_name="Borsele")
    content = b"<eml>counted votes from github</eml>"
    importer = make_importer(
        EML510bImporter, election_config=election_config, eml_file=NamedBytesIO(content, "input.eml.xml")
    )

    importer._store_eml(region)

    doc = ElectionDocument.objects.get()
    assert default_storage.open(doc.storage_key).read() == content
    assert doc.size == len(content)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("importer_cls", "expected_label"),
    [(EML510bImporter, "Telling_GSB"), (EML510dImporter, "Totaaltelling_CSB")],
)
def test_store_eml_filename_without_parent(importer_cls, expected_label, tmp_path):
    election_config = ElectionConfigFactory(identifier="AB2023")
    region = RegionFactory(parent=None, region_number="654", region_name="Borsele")
    importer = make_importer(importer_cls, election_config=election_config, eml_file=NamedBytesIO(b"<eml/>", "x.xml"))

    importer._store_eml(region)

    doc = ElectionDocument.objects.get()
    assert doc.storage_key == f"AB2023/AB2023_{expected_label}_654_Borsele.eml.xml"


@pytest.mark.django_db
def test_store_eml_filename_with_parent_sanitizes_special_characters():
    election_config = ElectionConfigFactory(identifier="AB2023")
    parent = RegionFactory(region_number="1", region_name="Scheldestromen (Test)")
    region = RegionFactory(
        election=parent.election,
        parent=parent,
        region_number="654",
        region_name="'s-Gravenhage/Voorburg",
    )
    importer = make_importer(
        EML510bImporter, election_config=election_config, eml_file=NamedBytesIO(b"<eml/>", "x.xml")
    )

    importer._store_eml(region)

    doc = ElectionDocument.objects.get()
    assert doc.storage_key == "AB2023/AB2023_Telling_GSB_1_Scheldestromen_Test_654_s-GravenhageVoorburg.eml.xml"


@pytest.mark.django_db
def test_store_eml_updates_size_of_existing_document_on_reimport():
    election_config = ElectionConfigFactory(identifier="AB2023")
    region = RegionFactory(parent=None, region_number="654", region_name="Borsele")
    expected_storage_key = "AB2023/AB2023_Telling_GSB_654_Borsele.eml.xml"
    existing = ElectionDocumentFactory(
        storage_key=expected_storage_key,
        region=region,
        content_type="application/xml",
        file_type=ElectionDocument.FileType.EML510B,
        size=1,
    )
    content = b"<eml>corrected counts, longer than before</eml>"
    importer = make_importer(EML510bImporter, election_config=election_config, eml_file=NamedBytesIO(content, "x.xml"))

    importer._store_eml(region)

    assert ElectionDocument.objects.filter(storage_key=expected_storage_key).count() == 1
    existing.refresh_from_db()
    assert existing.size == len(content)
    assert default_storage.open(existing.storage_key).read() == content
