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
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from eml_import.utils.election_importer import ElectionImporter
from mainsite.management.commands import build_ingress_repo
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

CSB_DIR = "centraalstembureau/nederland"
GSB_DIR = "gemeente/amsterdam"
HSB_DIR = "hoofdstembureau/amsterdam"

OSV_CSV = "osv4-3_telling_tk2025.csv"

# Only the fields `read_eml_meta` looks for; the command never parses the body of a document.
EML = """\
<?xml version="1.0" encoding="UTF-8"?>
<EML xmlns="urn:oasis:names:tc:evs:schema:eml" xmlns:kr="http://www.kiesraad.nl/extensions" Id="{doc_type}">
    {managing_authority}
    <Election>
        <ElectionIdentifier Id="{election_id}">
            <kr:ElectionDomain>{domain}</kr:ElectionDomain>
        </ElectionIdentifier>
    </Election>
</EML>
"""
MANAGING_AUTHORITY = "<ManagingAuthority><AuthorityIdentifier>{authority}</AuthorityIdentifier></ManagingAuthority>"


@dataclass(frozen=True)
class Document:
    """One EML document to generate, named as the counting software would name its file."""

    name: str
    doc_type: str
    authority: str = ""  # ManagingAuthority: the gemeente or hoofdstembureau that filed it
    domain: str = "Nederland"  # kr:ElectionDomain: the body holding the election

    def render(self, election_id: str) -> str:
        authority = MANAGING_AUTHORITY.format(authority=self.authority) if self.authority else ""
        return EML.format(
            doc_type=self.doc_type, managing_authority=authority, election_id=election_id, domain=self.domain
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
    assert set(ElectionImporter._DOCUMENT_TYPES) <= set(EXCHANGE_LEVELS) | set(COUNTING_LEVELS)


def test_exchange_documents_are_zipped_under_their_own_name(replica):
    files = written_files(replica, "dob2pk/")

    assert list(files) == [
        f"dob2pk/{CSB_DIR}/Kandidatenlijsten_TK2025_Amsterdam.zip",
        f"dob2pk/{CSB_DIR}/Verkiezingsdefinitie_TK2025.zip",
    ]
    assert zip_names(files[f"dob2pk/{CSB_DIR}/Verkiezingsdefinitie_TK2025.zip"]) == [
        "Verkiezingsdefinitie_TK2025.eml.xml"
    ]


def test_counting_documents_nest_two_zips_deep(source, replica):
    upload = next(content for name, content in written_files(replica, f"dob1/{GSB_DIR}/").items())

    assert zip_names(upload) == ["Telling_TK2025_gemeente_Amsterdam.zip"]

    inner = zip_member(upload, "Telling_TK2025_gemeente_Amsterdam.zip")
    document = source / "Telling_TK2025_gemeente_Amsterdam.eml.xml"
    assert zip_member(inner, document.name) == document.read_bytes()


def test_the_control_protocol_export_rides_along_with_the_totaaltelling(replica):
    uploads = written_files(replica, f"dob1/{CSB_DIR}/")
    contents = [zip_names(upload) for upload in uploads.values()]

    assert ["Totaaltelling_TK2025.zip", OSV_CSV] in contents
    # Only the Totaaltelling is accompanied by it; the Resultaat travels alone.
    assert ["Resultaat_TK2025.zip"] in contents


def test_a_gemeente_and_a_kieskring_of_the_same_name_stay_apart(replica):
    folders = {name.rsplit("/", 1)[0] for name in written_files(replica, "dob1/")}

    assert folders == {f"dob1/{GSB_DIR}", f"dob1/{HSB_DIR}", f"dob1/{CSB_DIR}"}


def test_counting_levels_are_committed_bottom_up(replica):
    """The importer replays commits oldest first, so the counting order has to hold."""
    uploads = sorted(written_files(replica, "dob1/"), key=pushed_at)

    assert [name.split("/")[1] for name in uploads] == [
        "gemeente",
        "hoofdstembureau",
        "centraalstembureau",
        "centraalstembureau",
    ]


def test_each_branch_is_created_from_main(run, replica):
    commands = git_commands(run)
    created = [index for index, command in enumerate(commands) if command[:2] == ["checkout", "-b"]]

    assert [commands[index][2] for index in created] == [EXCHANGE_BRANCH, COUNTING_BRANCH]
    assert all(commands[index - 1] == ["checkout", "main"] for index in created)


def test_every_org_gets_its_own_commit(run, replica):
    # Each branch opens with a scaffolding commit. The exchange branch then has the national
    # definition and the Amsterdam candidate list; the counting branch the gemeente, the
    # kieskring, and the central stembureau's Totaaltelling and Resultaat together.
    assert commits_per_branch(run) == {"main": 1, EXCHANGE_BRANCH: 3, COUNTING_BRANCH: 4}


def test_commits_carry_the_given_author(run, replica):
    environments = [call.kwargs["env"] for call in run.call_args_list if call.args[0][1] == "commit"]

    assert {env["GIT_AUTHOR_NAME"] for env in environments} == {"Auto Import"}
    assert {env["GIT_AUTHOR_EMAIL"] for env in environments} == {"auto-import@localhost"}


def test_single_commit_mode_collapses_a_branch_into_one_commit(run, source, tmp_path):
    build(source, tmp_path / "replica", commit_mode="single")

    assert commits_per_branch(run) == {"main": 1, EXCHANGE_BRANCH: 2, COUNTING_BRANCH: 2}


def test_rebuilding_the_same_source_is_reproducible(run, source, tmp_path):
    first = build(source, tmp_path / "first")
    second = build(source, tmp_path / "second")

    assert written_files(first) == written_files(second)


def test_branches_are_named_after_the_election(run, source, tmp_path):
    build(source, tmp_path / "replica", election_id="GR2026")

    created = [command[2] for command in git_commands(run) if command[:2] == ["checkout", "-b"]]
    assert created == ["auto-gr2026-uit", "auto-gr2026-tel"]


def test_refuses_a_source_without_usable_documents(run, tmp_path):
    empty = write_source(tmp_path / "source", documents=[])

    with pytest.raises(CommandError, match="No usable EML documents"):
        build(empty, tmp_path / "replica")


def test_refuses_to_rebuild_an_election_that_is_already_there(run, source, tmp_path):
    # Every git call succeeds now, the branch lookup included: the branches are already there.
    run.side_effect = lambda argv, **_: subprocess.CompletedProcess(argv, 0, "", "")

    with pytest.raises(CommandError, match=f"{EXCHANGE_BRANCH} already exists"):
        build(source, tmp_path / "replica")


def test_refuses_a_destination_that_is_not_a_git_repository(run, source, tmp_path):
    dest = tmp_path / "replica"
    dest.mkdir()
    (dest / "something.txt").write_text("in the way")

    with pytest.raises(CommandError, match="not a git repository"):
        build(source, dest)
