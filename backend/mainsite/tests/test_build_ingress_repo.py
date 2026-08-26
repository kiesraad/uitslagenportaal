"""
Tests for the `build_ingress_repo` dev command.

The source documents are generated per test rather than read from a fixture folder: the command
only reads four fields out of an EML file, so a handful of lines of XML each is enough, and a
generated set can cover shapes no single real election has.

Git is mocked out, so the files the command writes all stay in the working tree instead of being
carried off onto branches. That is enough to check what matters: which branch each document was
written for (`dob2pk/` vs `dob1/`), how the zips nest, and how the work was spread over commits.
"""

import io
import subprocess
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from eml_import.utils.file_handler import BaseFileHandler
from mainsite.management.commands import build_ingress_repo
from mainsite.management.commands._corrigenda import corrigenda_for, draw_corrigenda
from mainsite.management.commands.build_ingress_repo import (
    COUNTING_LEVELS,
    EXCHANGE_LEVELS,
    file_slug,
    folder_slug,
)
from mainsite.utils.eml_type import EmlType

ELECTION_ID = "TK2025"
EXCHANGE_BRANCH = "auto-tk2025-uit"
COUNTING_BRANCH = "auto-tk2025-tel"

ELECTION_DAY = "2025-10-29"
FIRST_COUNTING_COMMIT = f"{ELECTION_DAY}T09:00:00"

CSB_DIR = "centraalstembureau/nederland"
GSB_DIR = "gemeente/amsterdam"
HSB_DIR = "hoofdstembureau/amsterdam"

OSV_CSV = "osv4-3_telling_tk2025.csv"  # A control protocol export, dropped beside the EML files

# Only the fields `read_eml_meta` looks for; the command never parses the body of a document.
EML = """\
<?xml version="1.0" encoding="UTF-8"?>
<EML xmlns="urn:oasis:names:tc:evs:schema:eml" xmlns:kr="http://www.kiesraad.nl/extensions" Id="{doc_type}">
    {managing_authority}
    <Election>
        <ElectionIdentifier Id="{election_id}">
            <kr:ElectionDomain>{domain}</kr:ElectionDomain>
            {election_date}
        </ElectionIdentifier>
    </Election>
</EML>
"""
MANAGING_AUTHORITY = "<ManagingAuthority><AuthorityIdentifier>{authority}</AuthorityIdentifier></ManagingAuthority>"
ELECTION_DATE = "<kr:ElectionDate>{election_date}</kr:ElectionDate>"


@dataclass(frozen=True)
class Document:
    """One EML document to generate, named as the counting software would name its file."""

    name: str
    doc_type: str
    authority: str = ""  # ManagingAuthority: the gemeente or hoofdstembureau that filed it
    domain: str = "Nederland"  # kr:ElectionDomain: the body holding the election
    election_date: str = ELECTION_DAY  # kr:ElectionDate: the day the election is held

    def render(self, election_id: str) -> str:
        authority = MANAGING_AUTHORITY.format(authority=self.authority) if self.authority else ""
        election_date = ELECTION_DATE.format(election_date=self.election_date) if self.election_date else ""
        return EML.format(
            doc_type=self.doc_type,
            managing_authority=authority,
            election_id=election_id,
            domain=self.domain,
            election_date=election_date,
        )


# A Tweede Kamer election: counted per gemeente, totalled per kieskring, published nationally.
# Gemeente and kieskring Amsterdam share a name, which the counting levels have to keep apart.
DOCUMENTS = [
    Document("Verkiezingsdefinitie_TK2025", EmlType.EML_110a),
    Document("Kandidatenlijsten_TK2025_Amsterdam", EmlType.EML_230b),
    Document("Telling_TK2025_gemeente_Amsterdam", EmlType.EML_510b, authority="Amsterdam"),
    Document("Telling_TK2025_kieskring_Amsterdam", EmlType.EML_510c, authority="Amsterdam"),
    Document("Totaaltelling_TK2025", EmlType.EML_510d),
    Document("Resultaat_TK2025", EmlType.EML_520),
]


# A national election (TK, EP): the central stembureau names no election domain, and only its
# definition goes without a managing authority as well.
NATIONAL_DOCUMENTS = [
    Document("Verkiezingsdefinitie_TK2025", EmlType.EML_110a, domain=""),
    Document("Kandidatenlijsten_TK2025_Amsterdam", EmlType.EML_230b, authority="De Kiesraad", domain=""),
]


def write_source(folder: Path, documents=DOCUMENTS, election_id: str = ELECTION_ID) -> Path:
    folder.mkdir(parents=True)
    for document in documents:
        (folder / f"{document.name}.eml.xml").write_text(document.render(election_id), encoding="utf-8")
    # The control protocol export the counting software drops next to the Totaaltelling.
    (folder / OSV_CSV).write_text("Verkiezingnummer;Type\n", encoding="utf-8")
    return folder


def succeed_but_report_missing_branches(argv, **_):
    """Let every git call succeed, except the branch lookup that must report "not there yet"."""
    return subprocess.CompletedProcess(argv, 1 if argv[1] == "rev-parse" else 0, "", "")


@pytest.fixture
def run():
    with mock.patch.object(build_ingress_repo.subprocess, "run") as run:
        run.side_effect = succeed_but_report_missing_branches
        yield run


@pytest.fixture
def source(tmp_path) -> Path:
    return write_source(tmp_path / "source")


def build(source: Path, dest: Path, election_id: str = ELECTION_ID, **options) -> Path:
    """Build a replica, with corrigenda off unless a test asks for them."""
    options.setdefault("corrigenda_rate", 0)
    call_command("build_ingress_repo", source=str(source), dest=str(dest), election_id=election_id, **options)
    return dest


@pytest.fixture
def replica(run, source, tmp_path) -> Path:
    return build(source, tmp_path / "replica")


def git_commands(run) -> list[list[str]]:
    """Every git invocation the command made, without the noise of `--quiet`."""
    return [[arg for arg in call.args[0][1:] if arg != "--quiet"] for call in run.call_args_list]


def commits_per_branch(run) -> dict[str, int]:
    """How many commits landed on each branch, following the checkouts between them."""
    counts: dict[str, int] = {}
    branch = "main"
    for command in git_commands(run):
        if command[0] == "checkout":
            branch = command[-1]
        elif command[0] == "commit":
            counts[branch] = counts.get(branch, 0) + 1
    return counts


def commit_dates_per_branch(run) -> dict[str, list[str]]:
    """The date every commit claims, per branch, following the checkouts between them."""
    dates: dict[str, list[str]] = {}
    branch = "main"
    for call in run.call_args_list:
        command = call.args[0][1:]
        if command[0] == "checkout":
            branch = command[-1]
        elif command[0] == "commit":
            dates.setdefault(branch, []).append(call.kwargs["env"]["GIT_AUTHOR_DATE"])
    return dates


def counting_commit_dates(dates: dict[str, list[str]]) -> list[str]:
    """The counting branch's uploads, without the scaffolding commit each branch opens with."""
    _scaffolding, *uploads = dates[COUNTING_BRANCH]
    return uploads


def written_files(dest: Path, prefix: str = "") -> dict[str, bytes]:
    files = {
        str(path.relative_to(dest)).replace("\\", "/"): path.read_bytes() for path in dest.rglob("*") if path.is_file()
    }
    return {name: content for name, content in sorted(files.items()) if name.startswith(prefix)}


def pushed_at(upload: str) -> str:
    """The moment an upload archive claims to have been pushed, from its filename."""
    return upload.removesuffix(".zip")[-15:]


def zip_names(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.namelist()


def zip_member(data: bytes, name: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read(name)


@pytest.mark.parametrize(
    ("name", "expected_folder", "expected_file"),
    [
        ("Aa en Hunze", "aa_en_hunze", "aa-en-hunze"),
        ("Alphen-Chaam", "alphen_chaam", "alphen-chaam"),
        ("'s-Gravenhage", "s_gravenhage", "s-gravenhage"),
        ("Noardeast-Fryslân", "noardeast_fryslan", "noardeast-fryslan"),
    ],
)
def test_slugs_fold_punctuation_into_the_separator(name, expected_folder, expected_file):
    assert folder_slug(name) == expected_folder
    assert file_slug(name) == expected_file


def test_every_document_type_the_importer_reads_is_placed_on_a_branch():
    """Anything ElectionImporter would import must end up in the replica, whatever the election."""
    assert set(BaseFileHandler._DOCUMENT_TYPES) <= set(EXCHANGE_LEVELS) | set(COUNTING_LEVELS)


def test_exchange_documents_are_zipped_under_their_own_name(replica):
    files = written_files(replica, "dob2pk/")

    assert list(files) == [
        f"dob2pk/{CSB_DIR}/Kandidatenlijsten_TK2025_Amsterdam.zip",
        f"dob2pk/{CSB_DIR}/Verkiezingsdefinitie_TK2025.zip",
    ]
    assert zip_names(files[f"dob2pk/{CSB_DIR}/Verkiezingsdefinitie_TK2025.zip"]) == [
        "Verkiezingsdefinitie_TK2025.eml.xml"
    ]


def test_a_counting_upload_nests_the_eml_document_and_nothing_else(source, replica):
    """The real uploads carry the control protocol export too, but the importer reads only XML."""
    upload = next(content for name, content in written_files(replica, f"dob1/{GSB_DIR}/").items())

    assert zip_names(upload) == ["Telling_TK2025_gemeente_Amsterdam.zip"]

    inner = zip_member(upload, "Telling_TK2025_gemeente_Amsterdam.zip")
    document = source / "Telling_TK2025_gemeente_Amsterdam.eml.xml"
    assert zip_member(inner, document.name) == document.read_bytes()
    assert not [name for name in written_files(replica) if name.endswith(".csv")]


def test_a_national_central_stembureau_keeps_its_documents_together(run, tmp_path):
    """
    Its definition names neither a domain nor an authority, but belongs with the rest.

    That definition is also collected first: the importer replays commits oldest first, and a
    candidate list needs its election.
    """
    source = write_source(tmp_path / "national", documents=NATIONAL_DOCUMENTS)

    replica = build(source, tmp_path / "replica")
    exchange, _, _ = build_ingress_repo.Command()._collect_uploads(source)

    folder = f"dob2pk/centraalstembureau/{folder_slug(build_ingress_repo.NATIONAL_CSB)}"
    assert list(written_files(replica, "dob2pk/")) == [
        f"{folder}/Kandidatenlijsten_TK2025_Amsterdam.zip",
        f"{folder}/Verkiezingsdefinitie_TK2025.zip",
    ]
    assert [upload.path.name for upload in exchange] == [
        "Verkiezingsdefinitie_TK2025.eml.xml",
        "Kandidatenlijsten_TK2025_Amsterdam.eml.xml",
    ]


def test_counting_uploads_are_filed_per_organisation_and_committed_bottom_up(replica):
    """
    A gemeente counts, its hoofdstembureau totals the kieskring, the central stembureau publishes.

    The importer replays commits oldest first, so that order has to hold. Gemeente and kieskring
    Amsterdam share a name, and each still gets a folder of its own.
    """
    uploads = sorted(written_files(replica, "dob1/"), key=pushed_at)

    assert [name.rsplit("/", 1)[0] for name in uploads] == [
        f"dob1/{GSB_DIR}",
        f"dob1/{HSB_DIR}",
        f"dob1/{CSB_DIR}",
        f"dob1/{CSB_DIR}",
    ]


def test_each_branch_is_created_from_main(run, replica):
    commands = git_commands(run)
    created = [index for index, command in enumerate(commands) if command[:2] == ["checkout", "-b"]]

    assert [commands[index][2] for index in created] == [EXCHANGE_BRANCH, COUNTING_BRANCH]
    assert all(commands[index - 1] == ["checkout", "main"] for index in created)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        # Per organisation, each branch opens with a scaffolding commit. The exchange branch then
        # has the national definition and the Amsterdam candidate list; the counting branch the
        # gemeente, the kieskring, and the central stembureau's Totaaltelling and Resultaat together.
        ("per-org", {"main": 1, EXCHANGE_BRANCH: 3, COUNTING_BRANCH: 4}),
        # Everything a branch holds collapses into the single commit behind its scaffolding.
        ("single", {"main": 1, EXCHANGE_BRANCH: 2, COUNTING_BRANCH: 2}),
    ],
)
def test_the_commit_mode_decides_how_the_uploads_are_spread(run, source, tmp_path, mode, expected):
    build(source, tmp_path / "replica", commit_mode=mode)

    assert commits_per_branch(run) == expected


def test_counting_starts_on_election_day_and_the_exchange_comes_before_it(run, replica):
    """The dates come from the documents' own kr:ElectionDate, not from the election id."""
    dates = commit_dates_per_branch(run)

    assert min(counting_commit_dates(dates)) == FIRST_COUNTING_COMMIT
    assert max(dates[EXCHANGE_BRANCH]) < FIRST_COUNTING_COMMIT


def test_the_election_date_is_taken_from_any_document_when_the_definition_has_none(run, tmp_path):
    """Every EML type carries the date, so a source without a dated definition still schedules."""
    documents = [
        Document("Verkiezingsdefinitie_TK2025", EmlType.EML_110a, election_date=""),
        Document("Telling_TK2025_gemeente_Amsterdam", EmlType.EML_510b, authority="Amsterdam"),
    ]

    build(write_source(tmp_path / "source", documents=documents), tmp_path / "replica")

    assert min(counting_commit_dates(commit_dates_per_branch(run))) == FIRST_COUNTING_COMMIT


def test_commits_carry_the_given_author(run, replica):
    environments = [call.kwargs["env"] for call in run.call_args_list if call.args[0][1] == "commit"]

    assert {env["GIT_AUTHOR_NAME"] for env in environments} == {"Auto Import"}
    assert {env["GIT_AUTHOR_EMAIL"] for env in environments} == {"auto-import@localhost"}


@pytest.mark.parametrize(
    ("documents", "message"),
    [
        ([], "No usable EML documents"),
        (
            [Document(document.name, document.doc_type, election_date="") for document in DOCUMENTS],
            "No kr:ElectionDate",
        ),
    ],
    ids=["nothing-to-import", "no-election-date"],
)
def test_refuses_a_source_it_cannot_build_from(run, tmp_path, documents, message):
    source = write_source(tmp_path / "source", documents=documents)

    with pytest.raises(CommandError, match=message):
        build(source, tmp_path / "replica")


def test_an_empty_repository_on_another_default_branch_is_pointed_at_main(run, source, tmp_path):
    """`git init` elsewhere may have left HEAD on `master`; the branches are built off `main`."""
    dest = tmp_path / "replica"
    (dest / ".git").mkdir(parents=True)

    build(source, dest)

    assert ["symbolic-ref", "HEAD", "refs/heads/main"] in git_commands(run)
    # The repository was adopted as it is, not re-initialised over the top of it.
    assert not [command for command in git_commands(run) if command[0] == "init"]


def branches_already_there(dest: Path, run) -> None:
    """Let every git call succeed, the branch lookup included: the branches are already there."""
    run.side_effect = lambda argv, **_: subprocess.CompletedProcess(argv, 0, "", "")


def a_repository_without_main(dest: Path, run) -> None:
    """Keep reporting the branches as missing, but let HEAD resolve: this repository has commits."""
    (dest / ".git").mkdir(parents=True)
    run.side_effect = lambda argv, **_: subprocess.CompletedProcess(
        argv, 1 if argv[1] == "rev-parse" and argv[-1].startswith("refs/heads/") else 0, "", ""
    )


def a_folder_that_is_not_a_repository(dest: Path, run) -> None:
    dest.mkdir()
    (dest / "something.txt").write_text("in the way")


@pytest.mark.parametrize(
    ("prepare", "message"),
    [
        (branches_already_there, f"{EXCHANGE_BRANCH} already exists"),
        (a_repository_without_main, "has commits but no main branch"),
        (a_folder_that_is_not_a_repository, "not a git repository"),
    ],
)
def test_refuses_a_destination_it_cannot_build_into(run, source, tmp_path, prepare, message):
    dest = tmp_path / "replica"
    prepare(dest, run)

    with pytest.raises(CommandError, match=message):
        build(source, dest)


# Corrigenda ---------------------------------------------------------------------------------

# A Telling that balances, so the invariants below start out true: four polling stations, two
# parties of two candidates each. Every candidate clears MIN_CANDIDATE_VOTES and there are enough
# stations to host MAX_CORRIGENDA errors that share no candidate. The municipality totals are
# summed from the stations rather than written out, which is what keeps the fixture itself honest.
# Columns: polling station, votes per party, rejected votes, voting passes, proxies, ballots cast.
POLLING_STATIONS = [
    ("SB1", {"1": [40, 30], "2": [25, 15]}, {"ongeldig": 3, "blanco": 2}, 100, 15, 200),
    ("SB2", {"1": [22, 18], "2": [35, 26]}, {"ongeldig": 4, "blanco": 1}, 90, 16, 180),
    ("SB3", {"1": [31, 12], "2": [19, 28]}, {"ongeldig": 2, "blanco": 3}, 80, 15, 170),
    ("SB4", {"1": [17, 24], "2": [41, 11]}, {"ongeldig": 5, "blanco": 2}, 85, 15, 190),
]
PARTY_NAMES = {"1": "Eerste Partij", "2": "Tweede Partij"}

TELLING_CREATED_AT = "2025-10-29T21:14:07.123"
COUNTED_GEMEENTE = "Amsterdam"
COUNTED_TELLING = "Telling_TK2025_gemeente_Amsterdam"


def _selection_xml(votes: dict[str, list[int]]) -> str:
    """The interleaved party/candidate selections of one block, in the order the EML prescribes."""
    lines = []
    for party, candidates in votes.items():
        lines.append(
            f'<Selection><AffiliationIdentifier Id="{party}">'
            f"<RegisteredName>{PARTY_NAMES[party]}</RegisteredName>"
            f"</AffiliationIdentifier><ValidVotes>{sum(candidates)}</ValidVotes></Selection>"
        )
        for number, valid_votes in enumerate(candidates, start=1):
            lines.append(
                f'<Selection><Candidate><CandidateIdentifier Id="{number}"/></Candidate>'
                f"<ValidVotes>{valid_votes}</ValidVotes></Selection>"
            )
    return "\n            ".join(lines)


def _block_xml(votes, rejected, passes, proxies, cast) -> str:
    """The counts closing a block: what was counted, what was rejected, and who was admitted."""
    counted = sum(sum(candidates) for candidates in votes.values())
    return f"""{_selection_xml(votes)}
            <Cast>{cast}</Cast>
            <TotalCounted>{counted}</TotalCounted>
            <RejectedVotes ReasonCode="ongeldig">{rejected["ongeldig"]}</RejectedVotes>
            <RejectedVotes ReasonCode="blanco">{rejected["blanco"]}</RejectedVotes>
            <UncountedVotes ReasonCode="geldige stempassen">{passes}</UncountedVotes>
            <UncountedVotes ReasonCode="geldige volmachtbewijzen">{proxies}</UncountedVotes>
            <UncountedVotes ReasonCode="toegelaten kiezers">{passes + proxies}</UncountedVotes>
            <UncountedVotes ReasonCode="meer getelde stembiljetten">0</UncountedVotes>
            <UncountedVotes ReasonCode="minder getelde stembiljetten">0</UncountedVotes>"""


def render_telling(
    election_id: str = ELECTION_ID,
    created_at: str = TELLING_CREATED_AT,
    stations=POLLING_STATIONS,
) -> str:
    """A complete 510b, with its municipality block summed from its polling stations."""
    totals: dict[str, list[int]] = {}
    for _, votes, *_ in stations:
        for party, candidates in votes.items():
            running = totals.setdefault(party, [0] * len(candidates))
            for index, valid_votes in enumerate(candidates):
                running[index] += valid_votes

    units = "\n          ".join(
        f"""<ReportingUnitVotes>
            <ReportingUnitIdentifier Id="1884::{station}">Stembureau {station}</ReportingUnitIdentifier>
            {_block_xml(votes, rejected, passes, proxies, cast)}
          </ReportingUnitVotes>"""
        for station, votes, rejected, passes, proxies, cast in stations
    )
    total_block = _block_xml(
        totals,
        {key: sum(station[2][key] for station in stations) for key in ("ongeldig", "blanco")},
        sum(station[3] for station in stations),
        sum(station[4] for station in stations),
        sum(station[5] for station in stations),
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<EML xmlns="urn:oasis:names:tc:evs:schema:eml" xmlns:kr="http://www.kiesraad.nl/extensions" Id="510b">
  <ManagingAuthority><AuthorityIdentifier Id="1884">{COUNTED_GEMEENTE}</AuthorityIdentifier></ManagingAuthority>
  <kr:CreationDateTime>{created_at}</kr:CreationDateTime>
  <Count>
    <Election>
      <ElectionIdentifier Id="{election_id}">
        <kr:ElectionDomain>Nederland</kr:ElectionDomain>
        <kr:ElectionDate>{ELECTION_DAY}</kr:ElectionDate>
      </ElectionIdentifier>
      <Contests>
        <Contest>
          <ContestIdentifier Id="geen"/>
          <TotalVotes>
            {total_block}
          </TotalVotes>
          {units}
        </Contest>
      </Contests>
    </Election>
  </Count>
</EML>
"""


EML_NS = {"e": "urn:oasis:names:tc:evs:schema:eml"}
VALID_VOTES_TAG = "{urn:oasis:names:tc:evs:schema:eml}ValidVotes"
CREATION_DATE_TIME_TAG = "{http://www.kiesraad.nl/extensions}CreationDateTime"


@pytest.fixture
def counted_source(tmp_path) -> Path:
    """A source whose Telling has a real body, so corrigenda have counts to deviate from."""
    others = [document for document in DOCUMENTS if document.doc_type != EmlType.EML_510b]
    folder = write_source(tmp_path / "counted", documents=others)
    (folder / f"{COUNTED_TELLING}.eml.xml").write_text(render_telling(), encoding="utf-8")
    return folder


@pytest.fixture
def corrected(run, counted_source, tmp_path) -> Path:
    """A replica whose Telling was corrected three times before its final upload."""
    return build(counted_source, tmp_path / "replica", corrigenda_rate=0.9, seed=0)


def telling_revisions(replica: Path, directory: str = f"dob1/{GSB_DIR}/") -> list[bytes]:
    """Every uploaded revision of the Telling in `directory`, oldest upload first."""
    uploads = sorted(written_files(replica, directory).items(), key=lambda item: pushed_at(item[0]))
    revisions = []
    for _, archive in uploads:
        inner = zip_member(archive, zip_names(archive)[0])
        revisions.append(zip_member(inner, zip_names(inner)[0]))
    return revisions


def valid_votes(document: bytes) -> list[int]:
    return [int(element.text) for element in ET.fromstring(document).iter(VALID_VOTES_TAG)]


def created_at(document: bytes) -> str:
    return ET.fromstring(document).find(f".//{CREATION_DATE_TIME_TAG}").text


def _reason(block, tag: str, reason_code: str) -> int:
    return sum(int(e.text) for e in block.iterfind(f"e:{tag}", EML_NS) if e.get("ReasonCode") == reason_code)


def _party_and_candidate_totals(block) -> tuple[dict[str, int], dict[str, int]]:
    """What each party claims in `block`, against what its candidates actually hold."""
    parties: dict[str, int] = {}
    candidates: dict[str, int] = {}
    party = None
    for selection in block.iterfind("e:Selection", EML_NS):
        votes = int(selection.find("e:ValidVotes", EML_NS).text)
        affiliation = selection.find("e:AffiliationIdentifier", EML_NS)
        if affiliation is not None:
            party = affiliation.get("Id")
            parties[party] = votes
            candidates[party] = 0
        else:
            candidates[party] += votes
    return parties, candidates


def balance_problems(document: bytes) -> list[str]:
    """
    Every way a 510b can fail to add up; empty means it balances.

    Deliberately written out here rather than imported from `_corrigenda`: a generator checked
    with its own arithmetic would only be proving itself self-consistent.
    """
    problems: list[str] = []
    contest = ET.fromstring(document).find(".//e:Contest", EML_NS)
    total = contest.find("e:TotalVotes", EML_NS)
    units = contest.findall("e:ReportingUnitVotes", EML_NS)

    summed: dict[str, int] = {}
    for name, block in [("municipality", total), *((f"station {i}", u) for i, u in enumerate(units))]:
        parties, candidates = _party_and_candidate_totals(block)
        counted = int(block.find("e:TotalCounted", EML_NS).text)
        if parties != candidates:
            problems.append(f"{name}: party totals {parties} do not match candidate sums {candidates}")
        if counted != sum(parties.values()):
            problems.append(f"{name}: TotalCounted {counted} is not the {sum(parties.values())} the parties hold")
        admitted = (
            _reason(block, "UncountedVotes", "toegelaten kiezers")
            + _reason(block, "UncountedVotes", "meer getelde stembiljetten")
            - _reason(block, "UncountedVotes", "minder getelde stembiljetten")
        )
        accounted = counted + _reason(block, "RejectedVotes", "ongeldig") + _reason(block, "RejectedVotes", "blanco")
        if admitted != accounted:
            problems.append(f"{name}: {admitted} admitted voters against {accounted} accounted ballots")
        if any(votes < 0 for votes in parties.values()) or any(votes < 0 for votes in candidates.values()):
            problems.append(f"{name}: negative votes")
        if block is not total:
            for party, votes in parties.items():
                summed[party] = summed.get(party, 0) + votes

    if summed != _party_and_candidate_totals(total)[0]:
        problems.append(f"municipality {_party_and_candidate_totals(total)[0]} is not the {summed} its stations count")
    return problems


def test_the_generated_telling_balances_to_begin_with():
    """The other corrigenda tests only mean something if the document they deviate from adds up."""
    assert balance_problems(render_telling().encode()) == []


def test_each_further_corrigendum_is_less_likely_than_the_one_before():
    names = [f"Telling_TK2025_gemeente_{index}.eml.xml" for index in range(4000)]

    assert {draw_corrigenda(name, rate=0, seed=0) for name in names} == {0}, "a rate of 0 draws none at all"

    drawn = Counter(draw_corrigenda(name, rate=0.3, seed=0) for name in names)

    assert sorted(drawn) == [0, 1, 2, 3], "a Telling is corrected between zero and three times"
    frequencies = [drawn[count] for count in sorted(drawn)]
    assert frequencies == sorted(frequencies, reverse=True), f"{frequencies} does not decay"


def test_a_telling_too_small_to_miscount_is_not_corrected(tmp_path):
    """A gemeente counting for a neighbouring body reports too few votes to get one wrong."""
    tiny = [("SB1", {"1": [1, 0], "2": [1, 0]}, {"ongeldig": 0, "blanco": 0}, 2, 0, 4)]
    document = tmp_path / f"{COUNTED_TELLING}.eml.xml"
    document.write_text(render_telling(stations=tiny), encoding="utf-8")

    assert draw_corrigenda(document.name, rate=1, seed=0) == 3, "the draw itself asks for three"
    assert corrigenda_for(document, rate=1, seed=0) == 0, "but there is nothing to correct"


def test_the_revisions_of_a_corrected_telling_converge_on_the_source(counted_source, corrected):
    """The uploads walk towards the source, so an import of the branch ends where the source is."""
    document = counted_source / f"{COUNTED_TELLING}.eml.xml"
    revisions = telling_revisions(corrected)

    assert len(revisions) == 4, "three corrigenda and the source itself"
    assert [balance_problems(revision) for revision in revisions] == [[]] * 4

    final = valid_votes(document.read_bytes())
    deviations = [
        sum(1 for votes, correct in zip(valid_votes(revision), final) if votes != correct) for revision in revisions
    ]

    assert deviations[0] > 0, "the first upload should still hold the errors the corrigenda fix"
    assert deviations[-1] == 0
    assert deviations == sorted(deviations, reverse=True), f"{deviations} does not converge"
    assert revisions[-1] == document.read_bytes(), "the last revision is the source file itself"


def test_every_revision_claims_to_precede_the_one_after_it(corrected):
    """A corrigendum is recognised by a newer kr:CreationDateTime under an unchanged filename."""
    stamps = [created_at(revision) for revision in telling_revisions(corrected)]

    assert stamps == sorted(stamps)
    assert len(set(stamps)) == len(stamps), f"{stamps} are not all distinct"
    assert stamps[-1] == TELLING_CREATED_AT, "the source keeps the moment it says it was created"


def test_a_corrected_telling_is_uploaded_once_per_revision(run, corrected):
    """
    Each upload is its own commit, so the importer replays them one correction at a time.

    A Telling is corrected before the kieskring and the country total it feeds into, so all four
    of its uploads sit in the gemeente phase.
    """
    # Three corrigenda on top of what the per-org row of the commit mode table counts.
    assert commits_per_branch(run) == {"main": 1, EXCHANGE_BRANCH: 3, COUNTING_BRANCH: 4 + 3}

    uploads = sorted(written_files(corrected, "dob1/"), key=pushed_at)
    assert [name.split("/")[1] for name in uploads] == [
        *["gemeente"] * 4,
        "hoofdstembureau",
        "centraalstembureau",
        "centraalstembureau",
    ]


def test_the_seed_decides_the_corrigenda(run, counted_source, tmp_path):
    """The same seed rebuilds the same repository byte for byte; another seed miscounts elsewhere."""
    first = build(counted_source, tmp_path / "first", corrigenda_rate=0.9, seed=0)
    again = build(counted_source, tmp_path / "again", corrigenda_rate=0.9, seed=0)
    other = build(counted_source, tmp_path / "other", corrigenda_rate=0.9, seed=1)

    assert written_files(first) == written_files(again)
    # On the counts rather than on the files: another seed can draw another number of corrigenda,
    # which would already tell the two trees apart by their archive names alone.
    assert [valid_votes(revision) for revision in telling_revisions(first)] != [
        valid_votes(revision) for revision in telling_revisions(other)
    ]


@pytest.mark.parametrize("rate", [-0.1, 1.5])
def test_refuses_a_corrigenda_rate_that_is_not_a_chance(run, counted_source, tmp_path, rate):
    with pytest.raises(CommandError, match="--corrigenda-rate must be between 0 and 1"):
        build(counted_source, tmp_path / "replica", corrigenda_rate=rate)
