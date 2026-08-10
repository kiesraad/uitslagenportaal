import io
import zipfile
from datetime import timedelta

import pytest
from django.utils import timezone

from election.tests.factories import ElectionConfigFactory
from eml_import.models import BranchType, ImportedCommit
from eml_import.tests.factories import ImportedCommitFactory
from eml_import.tests.fakes import FakeCommit, FakeFile, FakeGithub, FakeRepo
from eml_import.utils import github_eml_importer
from eml_import.utils.github_eml_importer import COMMIT_BATCH_SIZE, GithubEmlImporter

XML_110A = b"<EML Id='110a'/>"
XML_230B = b"<EML Id='230b'/>"
XML_510B = b"<EML Id='510b'/>"

BRANCH_EXCHANGE = "exchange"
BRANCH_COUNTING_RESULTS = "counting-results"


def zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def as_pairs(files) -> list[tuple[str, bytes]]:
    return [(file.filename, file.getvalue()) for file in files]


@pytest.fixture
def fake_repo(monkeypatch, settings):
    """Build a FakeRepo and make GithubEmlImporter construct itself against it.

    ``commits`` is either the commits of the exchange branch, or a branch name -> commits mapping.
    """
    settings.GITHUB_TOKEN = "token"  # Auth.Token rejects None, and the setting is unset in CI
    settings.GITHUB_INGRESS_REPO = "owner/repo"

    def build(commits, contents=None):
        branches = commits if isinstance(commits, dict) else {BRANCH_EXCHANGE: commits}
        repo = FakeRepo(branches, contents)
        monkeypatch.setattr(github_eml_importer, "Github", lambda auth, per_page: FakeGithub(repo))
        return repo

    return build


@pytest.fixture
def election_config():
    """An unsaved config, for the tests that do not touch the database."""
    return ElectionConfigFactory.build(
        gh_exchange_branch=BRANCH_EXCHANGE, gh_counting_results_branch=BRANCH_COUNTING_RESULTS
    )


@pytest.fixture
def stored_election_config(db):
    """A saved config, for the run() tests that record their progress."""
    return ElectionConfigFactory(gh_exchange_branch=BRANCH_EXCHANGE, gh_counting_results_branch=BRANCH_COUNTING_RESULTS)


@pytest.fixture
def imported_batches(monkeypatch):
    """Capture what run() hands to ElectionImporter, without parsing any real EML."""
    batches = []

    class RecordingElectionImporter:
        def import_file_objects(self, files):
            batches.append(files)

    monkeypatch.setattr(github_eml_importer, "ElectionImporter", RecordingElectionImporter)
    return batches


def test_iterate_all_xml_files_yields_xml_and_unpacks_zip(fake_repo, election_config):
    repo = fake_repo(
        commits=[FakeCommit("head")],
        contents={
            "results/telling.xml": XML_510B,
            "results/bundle.zip": zip_bytes({"inner/kandidaten.xml": XML_230B, "inner/readme.txt": b"nope"}),
        },
    )
    files = [
        FakeFile("results/telling.xml"),
        FakeFile("results/bundle.zip"),
        FakeFile("results/notes.txt"),
    ]

    extracted = list(GithubEmlImporter(election_config)._iterate_all_xml_files(files))

    assert as_pairs(extracted) == [
        ("results/telling.xml", XML_510B),
        ("inner/kandidaten.xml", XML_230B),
    ]
    # Files with an unsupported extension are never fetched
    assert repo.calls_named("get_git_blob") == [
        ("get_git_blob", "results/telling.xml"),
        ("get_git_blob", "results/bundle.zip"),
    ]


@pytest.mark.parametrize("status", ["added", "modified", "renamed", "copied", "changed"])
def test_iterate_all_xml_files_imports_every_status_that_leaves_a_file_behind(fake_repo, election_config, status):
    fake_repo(commits=[FakeCommit("head")], contents={"telling.xml": XML_510B})

    extracted = list(GithubEmlImporter(election_config)._iterate_all_xml_files([FakeFile("telling.xml", status)]))

    assert as_pairs(extracted) == [("telling.xml", XML_510B)]


@pytest.mark.parametrize("status", ["removed", "unchanged"])
def test_iterate_all_xml_files_skips_removed_and_unchanged(fake_repo, election_config, status):
    repo = fake_repo(commits=[FakeCommit("head")], contents={"telling.xml": XML_510B})

    extracted = list(GithubEmlImporter(election_config)._iterate_all_xml_files([FakeFile("telling.xml", status)]))

    assert extracted == []
    assert repo.calls_named("get_git_blob") == []


def test_iterate_all_xml_files_unpacks_nested_zip(fake_repo, election_config):
    inner = zip_bytes({"telling.xml": XML_510B})
    fake_repo(
        commits=[FakeCommit("head")],
        contents={"outer.zip": zip_bytes({"nested/inner.zip": inner})},
    )

    extracted = list(GithubEmlImporter(election_config)._iterate_all_xml_files([FakeFile("outer.zip")]))

    # Named after the entry inside the archive, not after the zip it arrived in
    assert as_pairs(extracted) == [("telling.xml", XML_510B)]


def test_iterate_branches_yields_the_exchange_branch_before_the_counting_results_branch(fake_repo, election_config):
    fake_repo(commits=[])

    branches = list(GithubEmlImporter(election_config)._iterate_branches())

    assert branches == [(BranchType.EXCHANGE, BRANCH_EXCHANGE), (BranchType.COUNTING_RESULTS, BRANCH_COUNTING_RESULTS)]


def test_iterate_branches_skips_branches_that_are_not_configured(fake_repo, election_config):
    fake_repo(commits=[])
    election_config.gh_exchange_branch = None

    branches = list(GithubEmlImporter(election_config)._iterate_branches())

    assert branches == [(BranchType.COUNTING_RESULTS, BRANCH_COUNTING_RESULTS)]


def test_get_next_batch_of_files_starts_at_the_oldest_commit(fake_repo, election_config):
    repo = fake_repo(
        commits=[
            FakeCommit("oldest", [FakeFile("a.xml")]),
            FakeCommit("middle", [FakeFile("b.xml")]),
            FakeCommit("newest", [FakeFile("c.xml")]),
        ]
    )

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files(None, BRANCH_EXCHANGE)

    assert head_sha == "newest"
    # compare() excludes the base commit, so the oldest commit is fetched separately;
    # the two sources must not overlap
    assert [file.filename for file in files] == ["a.xml", "b.xml", "c.xml"]
    assert repo.calls_named("get_commits") == [("get_commits", BRANCH_EXCHANGE)]
    assert repo.calls_named("get_commit") == [("get_commit", "oldest")]
    assert repo.calls_named("compare") == [("compare", "oldest", "newest")]


def test_get_next_batch_of_files_caps_the_batch_size(fake_repo, election_config):
    commits = [FakeCommit(f"c{index}", [FakeFile(f"{index}.xml")]) for index in range(COMMIT_BATCH_SIZE + 2)]
    fake_repo(commits=commits)

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files(None, BRANCH_EXCHANGE)

    assert head_sha == f"c{COMMIT_BATCH_SIZE - 1}"
    assert len(files) == COMMIT_BATCH_SIZE


def test_get_next_batch_of_files_resumes_after_the_base_commit(fake_repo, election_config):
    repo = fake_repo(
        commits=[
            FakeCommit("imported", [FakeFile("already-done.xml")]),
            FakeCommit("next", [FakeFile("a.xml")]),
            FakeCommit("last", [FakeFile("b.xml")]),
        ]
    )

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files("imported", BRANCH_EXCHANGE)

    assert head_sha == "last"
    # The base commit's own files are not imported a second time
    assert [file.filename for file in files] == ["a.xml", "b.xml"]
    assert repo.calls_named("compare")[0] == ("compare", "imported", BRANCH_EXCHANGE)


def test_get_next_batch_of_files_returns_nothing_when_up_to_date(fake_repo, election_config):
    repo = fake_repo(commits=[FakeCommit("imported", [FakeFile("a.xml")])])

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files("imported", BRANCH_EXCHANGE)

    assert head_sha is None
    assert files == []
    # Bails out before fetching any files
    assert repo.calls_named("get_commit") == []
    assert repo.calls_named("compare") == [("compare", "imported", BRANCH_EXCHANGE)]


def test_get_next_batch_of_files_does_not_diff_a_single_commit(fake_repo, election_config):
    repo = fake_repo(
        commits=[
            FakeCommit("imported", [FakeFile("already-done.xml")]),
            FakeCommit("only", [FakeFile("a.xml")]),
        ]
    )

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files("imported", BRANCH_EXCHANGE)

    assert head_sha == "only"
    assert [file.filename for file in files] == ["a.xml"]
    # compare() is only used to list the commits; the files come from get_commit()
    assert repo.calls_named("compare") == [("compare", "imported", BRANCH_EXCHANGE)]
    assert repo.calls_named("get_commit") == [("get_commit", "only")]


def test_get_next_batch_of_files_uses_the_diff_when_it_has_fewer_than_300_files(fake_repo, election_config):
    first_commit_files = [FakeFile("a.xml")]
    diff_files = [FakeFile(f"pad_{index}.xml") for index in range(299)]
    repo = fake_repo(commits=[FakeCommit("first", first_commit_files), FakeCommit("second", diff_files)])

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files(None, BRANCH_EXCHANGE)

    assert head_sha == "second"
    assert [file.filename for file in files] == ["a.xml"] + [f"pad_{index}.xml" for index in range(299)]
    assert repo.calls_named("compare") == [("compare", "first", "second")]
    # The diff is small enough to use directly, without fetching each commit separately
    assert repo.calls_named("get_commit") == [("get_commit", "first")]


def test_get_next_batch_of_files_fetches_files_per_commit_when_the_diff_has_300_or_more_files(
    fake_repo, election_config
):
    first_commit_files = [FakeFile("a.xml")]
    diff_files = [FakeFile(f"pad_{index}.xml") for index in range(300)]
    repo = fake_repo(commits=[FakeCommit("first", first_commit_files), FakeCommit("second", diff_files)])

    head_sha, files = GithubEmlImporter(election_config)._get_next_batch_of_files(None, BRANCH_EXCHANGE)

    assert head_sha == "second"
    assert [file.filename for file in files] == ["a.xml"] + [f"pad_{index}.xml" for index in range(300)]
    # The diff is only used to measure its size; once it is 300 files or more, the files
    # are fetched per commit instead, at the cost of one extra request per commit
    assert repo.calls_named("compare") == [("compare", "first", "second")]
    assert repo.calls_named("get_commit") == [("get_commit", "first"), ("get_commit", "second")]


def test_run_imports_from_the_first_commit_and_records_progress(fake_repo, imported_batches, stored_election_config):
    fake_repo(
        commits=[
            FakeCommit("first", [FakeFile("verkiezingsdefinitie.xml")]),
            FakeCommit("second", [FakeFile("kandidatenlijst.xml")]),
        ],
        contents={"verkiezingsdefinitie.xml": XML_110A, "kandidatenlijst.xml": XML_230B},
    )

    file_count = GithubEmlImporter(stored_election_config).run()

    assert file_count == 2
    assert as_pairs(imported_batches[0]) == [
        ("verkiezingsdefinitie.xml", XML_110A),
        ("kandidatenlijst.xml", XML_230B),
    ]
    assert list(ImportedCommit.objects.values_list("election_config", "branch_type", "commit_sha")) == [
        (stored_election_config.pk, BranchType.EXCHANGE, "second")
    ]


def test_run_resumes_from_the_most_recently_imported_commit(fake_repo, imported_batches, stored_election_config):
    repo = fake_repo(
        commits=[FakeCommit("recent"), FakeCommit("new", [FakeFile("telling.xml")])],
        contents={"telling.xml": XML_510B},
    )
    ImportedCommitFactory(election_config=stored_election_config, commit_sha="recent")
    stale = ImportedCommitFactory(election_config=stored_election_config, commit_sha="stale")
    # created_at is auto_now_add, so age it afterwards to make insertion order
    # deliberately disagree with created_at order
    ImportedCommit.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(days=1))

    GithubEmlImporter(stored_election_config).run()

    assert repo.calls_named("compare")[0] == ("compare", "recent", BRANCH_EXCHANGE)
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]


def test_run_ignores_the_progress_of_other_elections_and_branch_types(
    fake_repo, imported_batches, stored_election_config
):
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    # Same branch type, other election
    ImportedCommitFactory(commit_sha="first")
    # Same election, other branch type
    ImportedCommitFactory(
        election_config=stored_election_config,
        branch_type=BranchType.COUNTING_RESULTS,
        commit_sha="first",
    )

    GithubEmlImporter(stored_election_config).run()

    # Neither row applies to this branch, so the exchange branch starts at its first commit
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]


def test_run_stays_on_the_exchange_branch_while_it_has_commits(fake_repo, imported_batches, stored_election_config):
    fake_repo(
        commits={
            BRANCH_EXCHANGE: [FakeCommit("exchange-1", [FakeFile("uitslag.xml")])],
            BRANCH_COUNTING_RESULTS: [FakeCommit("counting-1", [FakeFile("telling.xml")])],
        },
        contents={"uitslag.xml": XML_510B, "telling.xml": XML_510B},
    )

    GithubEmlImporter(stored_election_config).run()

    assert as_pairs(imported_batches[0]) == [("uitslag.xml", XML_510B)]
    assert list(ImportedCommit.objects.values_list("branch_type", "commit_sha")) == [
        (BranchType.EXCHANGE, "exchange-1"),
    ]


def test_run_continues_on_the_counting_results_branch_once_the_exchange_branch_is_imported(
    fake_repo, imported_batches, stored_election_config
):
    fake_repo(
        commits={
            BRANCH_EXCHANGE: [FakeCommit("exchange-1", [FakeFile("uitslag.xml")])],
            BRANCH_COUNTING_RESULTS: [FakeCommit("counting-1", [FakeFile("telling.xml")])],
        },
        contents={"uitslag.xml": XML_510B, "telling.xml": XML_510B},
    )
    ImportedCommitFactory(election_config=stored_election_config, commit_sha="exchange-1")

    file_count = GithubEmlImporter(stored_election_config).run()

    assert file_count == 1
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]
    assert list(ImportedCommit.objects.order_by("created_at").values_list("branch_type", "commit_sha")) == [
        (BranchType.EXCHANGE, "exchange-1"),
        (BranchType.COUNTING_RESULTS, "counting-1"),
    ]


def test_run_does_not_continue_on_the_counting_results_branch_when_the_exchange_batch_holds_no_xml(
    fake_repo, imported_batches, stored_election_config
):
    fake_repo(
        commits={
            BRANCH_EXCHANGE: [FakeCommit("exchange-1", [FakeFile("readme.txt")])],
            BRANCH_COUNTING_RESULTS: [FakeCommit("counting-1", [FakeFile("telling.xml")])],
        },
        contents={"telling.xml": XML_510B},
    )

    file_count = GithubEmlImporter(stored_election_config).run()

    # The exchange commit is consumed even though it holds nothing to import
    assert file_count == 0
    assert as_pairs(imported_batches[0]) == []
    assert list(ImportedCommit.objects.values_list("branch_type", "commit_sha")) == [
        (BranchType.EXCHANGE, "exchange-1"),
    ]


def test_run_does_nothing_when_no_branch_has_new_commits(fake_repo, imported_batches, stored_election_config):
    fake_repo(
        commits={
            BRANCH_EXCHANGE: [FakeCommit("exchange-1", [FakeFile("a.xml")])],
            BRANCH_COUNTING_RESULTS: [FakeCommit("counting-1", [FakeFile("b.xml")])],
        }
    )
    ImportedCommitFactory(election_config=stored_election_config, commit_sha="exchange-1")
    ImportedCommitFactory(
        election_config=stored_election_config,
        branch_type=BranchType.COUNTING_RESULTS,
        commit_sha="counting-1",
    )

    file_count = GithubEmlImporter(stored_election_config).run()

    assert file_count == 0
    assert imported_batches == []
    assert ImportedCommit.objects.count() == 2
