import io
import logging
import zipfile
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from election.tests.factories import ElectionConfigFactory
from eml_import.exceptions import GithubImportException
from eml_import.models import BranchType, ImportedCommit
from eml_import.tests.factories import ImportedCommitFactory
from eml_import.tests.fakes import FakeCommit, FakeFile, FakeGithub, FakeRepo
from eml_import.utils import github_eml_importer
from eml_import.utils.github_eml_importer import LOCK_TIMEOUT, GithubEmlFileHandler

XML_110A = b"<EML Id='110a'/>"
XML_230B = b"<EML Id='230b'/>"
XML_510B = b"<EML Id='510b'/>"

BRANCH_EXCHANGE = "exchange"
BRANCH_COUNTING_RESULTS = "counting-results"

INGRESS_REPO = "kiesraad/repo"


def zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def as_pairs(files) -> list[tuple[str, bytes]]:
    return [(file.filename, file.getvalue()) for file in files]


def warnings_of(caplog) -> list[str]:
    """The warnings the importer logged, which is the only trace a lock problem leaves."""
    return [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]


@pytest.fixture
def fake_repo(monkeypatch, settings):
    """Build a FakeRepo and make GithubEmlFileHandler construct itself against it.

    ``commits`` is either the commits of the exchange branch, or a branch name -> commits mapping.
    """
    settings.GITHUB_TOKEN = "token"  # Auth.Token rejects None, and the setting is unset in CI
    settings.GITHUB_INGRESS_REPO = INGRESS_REPO

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
    """Capture what run() hands to import_file_objects, without parsing any real EML."""
    batches = []

    def record_import(self, files):
        batches.append(files)

    monkeypatch.setattr(GithubEmlFileHandler, "import_file_objects", record_import)
    return batches


@pytest.fixture
def build_importer():
    """
    An importer already setup with the fake repo.
    """

    def build(election_config, repo):
        importer = GithubEmlFileHandler(election_config)
        importer.repo = repo
        return importer

    return build


def test_iterate_all_xml_files_yields_xml_and_unpacks_zip(fake_repo, build_importer, election_config):
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

    extracted = list(build_importer(election_config, repo)._iterate_all_xml_files(files))

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
def test_iterate_all_xml_files_imports_every_status_that_leaves_a_file_behind(
    fake_repo, build_importer, election_config, status
):
    repo = fake_repo(commits=[FakeCommit("head")], contents={"telling.xml": XML_510B})

    extracted = list(build_importer(election_config, repo)._iterate_all_xml_files([FakeFile("telling.xml", status)]))

    assert as_pairs(extracted) == [("telling.xml", XML_510B)]


@pytest.mark.parametrize("status", ["removed", "unchanged"])
def test_iterate_all_xml_files_skips_removed_and_unchanged(fake_repo, build_importer, election_config, status):
    repo = fake_repo(commits=[FakeCommit("head")], contents={"telling.xml": XML_510B})

    extracted = list(build_importer(election_config, repo)._iterate_all_xml_files([FakeFile("telling.xml", status)]))

    assert extracted == []
    assert repo.calls_named("get_git_blob") == []


def test_iterate_all_xml_files_unpacks_nested_zip(fake_repo, build_importer, election_config):
    inner = zip_bytes({"telling.xml": XML_510B})
    repo = fake_repo(
        commits=[FakeCommit("head")],
        contents={"outer.zip": zip_bytes({"nested/inner.zip": inner})},
    )

    extracted = list(build_importer(election_config, repo)._iterate_all_xml_files([FakeFile("outer.zip")]))

    # Named after the entry inside the archive, not after the zip it arrived in
    assert as_pairs(extracted) == [("telling.xml", XML_510B)]


def test_iterate_branches_yields_the_exchange_branch_before_the_counting_results_branch(fake_repo, election_config):
    fake_repo(commits=[])

    branches = list(GithubEmlFileHandler(election_config)._iterate_branches())

    assert branches == [(BranchType.EXCHANGE, BRANCH_EXCHANGE), (BranchType.COUNTING_RESULTS, BRANCH_COUNTING_RESULTS)]


def test_iterate_branches_skips_branches_that_are_not_configured(fake_repo, election_config):
    fake_repo(commits=[])
    election_config.gh_exchange_branch = None

    branches = list(GithubEmlFileHandler(election_config)._iterate_branches())

    assert branches == [(BranchType.COUNTING_RESULTS, BRANCH_COUNTING_RESULTS)]


def test_get_files_for_next_commit_starts_at_the_oldest_commit(fake_repo, build_importer, election_config):
    repo = fake_repo(
        commits=[
            FakeCommit("oldest", [FakeFile("a.xml")]),
            FakeCommit("middle", [FakeFile("b.xml")]),
            FakeCommit("newest", [FakeFile("c.xml")]),
        ]
    )

    head_sha, files = build_importer(election_config, repo)._get_files_for_next_commit(None, BRANCH_EXCHANGE)

    assert head_sha == "oldest"
    assert [file.filename for file in files] == ["a.xml"]
    assert repo.calls_named("get_commits") == [("get_commits", BRANCH_EXCHANGE)]
    assert repo.calls_named("get_commit") == [("get_commit", "oldest")]
    assert repo.calls_named("compare") == []


def test_get_files_for_next_commit_resumes_after_the_base_commit(fake_repo, build_importer, election_config):
    repo = fake_repo(
        commits=[
            FakeCommit("imported", [FakeFile("already-done.xml")]),
            FakeCommit("next", [FakeFile("a.xml")]),
            FakeCommit("last", [FakeFile("b.xml")]),
        ]
    )

    head_sha, files = build_importer(election_config, repo)._get_files_for_next_commit("imported", BRANCH_EXCHANGE)

    assert head_sha == "next"
    assert [file.filename for file in files] == ["a.xml"]
    assert repo.calls_named("compare")[0] == ("compare", "imported", BRANCH_EXCHANGE)


def test_get_files_for_next_commit_returns_nothing_when_up_to_date(fake_repo, build_importer, election_config):
    repo = fake_repo(commits=[FakeCommit("imported", [FakeFile("a.xml")])])

    head_sha, files = build_importer(election_config, repo)._get_files_for_next_commit("imported", BRANCH_EXCHANGE)

    assert head_sha is None
    assert files == []
    # Bails out before fetching any files
    assert repo.calls_named("get_commit") == []
    assert repo.calls_named("compare") == [("compare", "imported", BRANCH_EXCHANGE)]


def test_run_imports_from_the_first_commit_and_records_progress(fake_repo, imported_batches, stored_election_config):
    fake_repo(
        commits=[
            FakeCommit("first", [FakeFile("verkiezingsdefinitie.xml")]),
            FakeCommit("second", [FakeFile("kandidatenlijst.xml")]),
        ],
        contents={"verkiezingsdefinitie.xml": XML_110A, "kandidatenlijst.xml": XML_230B},
    )

    file_count = GithubEmlFileHandler(stored_election_config).run()

    assert file_count == 2
    assert as_pairs(imported_batches[0]) == [("verkiezingsdefinitie.xml", XML_110A)]
    assert as_pairs(imported_batches[1]) == [("kandidatenlijst.xml", XML_230B)]
    assert list(ImportedCommit.objects.values_list("election_config", "branch_type", "commit_sha")) == [
        (stored_election_config.pk, BranchType.EXCHANGE, "first"),
        (stored_election_config.pk, BranchType.EXCHANGE, "second"),
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

    GithubEmlFileHandler(stored_election_config).run()

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

    GithubEmlFileHandler(stored_election_config).run()

    # Neither row applies to this branch, so the exchange branch starts at its first commit
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]


def test_run_processes_exchange_before_counting_results(fake_repo, imported_batches, stored_election_config):
    fake_repo(
        commits={
            BRANCH_EXCHANGE: [FakeCommit("exchange-1", [FakeFile("uitslag.xml")])],
            BRANCH_COUNTING_RESULTS: [FakeCommit("counting-1", [FakeFile("telling.xml")])],
        },
        contents={"uitslag.xml": XML_510B, "telling.xml": XML_510B},
    )

    GithubEmlFileHandler(stored_election_config).run()

    assert as_pairs(imported_batches[0]) == [("uitslag.xml", XML_510B)]
    assert as_pairs(imported_batches[1]) == [("telling.xml", XML_510B)]
    assert list(ImportedCommit.objects.values_list("branch_type", "commit_sha")) == [
        (BranchType.EXCHANGE, "exchange-1"),
        (BranchType.COUNTING_RESULTS, "counting-1"),
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

    file_count = GithubEmlFileHandler(stored_election_config).run()

    assert file_count == 1
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]
    assert list(ImportedCommit.objects.order_by("created_at").values_list("branch_type", "commit_sha")) == [
        (BranchType.EXCHANGE, "exchange-1"),
        (BranchType.COUNTING_RESULTS, "counting-1"),
    ]


def test_run_continues_on_the_counting_results_branch_after_exchange_even_without_xml(
    fake_repo, imported_batches, stored_election_config
):
    fake_repo(
        commits={
            BRANCH_EXCHANGE: [FakeCommit("exchange-1", [FakeFile("readme.txt")])],
            BRANCH_COUNTING_RESULTS: [FakeCommit("counting-1", [FakeFile("telling.xml")])],
        },
        contents={"telling.xml": XML_510B},
    )

    file_count = GithubEmlFileHandler(stored_election_config).run()

    # The exchange commit is consumed even though it holds nothing to import
    assert file_count == 1
    assert as_pairs(imported_batches[0]) == []
    assert as_pairs(imported_batches[1]) == [("telling.xml", XML_510B)]
    assert list(ImportedCommit.objects.values_list("branch_type", "commit_sha")) == [
        (BranchType.EXCHANGE, "exchange-1"),
        (BranchType.COUNTING_RESULTS, "counting-1"),
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

    file_count = GithubEmlFileHandler(stored_election_config).run()

    assert file_count == 0
    assert imported_batches == []
    assert ImportedCommit.objects.count() == 2


@pytest.mark.parametrize("missing_setting", ["GITHUB_TOKEN", "GITHUB_INGRESS_REPO"])
def test_run_refuses_to_start_when_github_is_not_configured(fake_repo, settings, election_config, missing_setting):
    fake_repo(commits=[FakeCommit("head")])
    setattr(settings, missing_setting, "")
    importer = GithubEmlFileHandler(election_config)

    with pytest.raises(GithubImportException, match=missing_setting):
        importer.run()

    # Bails out before building a client, so nothing was ever asked of GitHub
    assert importer.gh is None
    assert importer.repo is None


def test_run_connects_to_the_configured_repository(fake_repo, imported_batches, stored_election_config):
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    importer = GithubEmlFileHandler(stored_election_config)

    importer.run()

    assert importer.gh.requested_repos == [INGRESS_REPO]


def test_run_skips_the_import_while_another_worker_holds_the_lock(
    fake_repo, imported_batches, stored_election_config, caplog
):
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    importer = GithubEmlFileHandler(stored_election_config)

    # Stand in for a second worker that is already importing this election
    with cache.lock(importer.cache_lock_key, timeout=LOCK_TIMEOUT):
        file_count = importer.run()

    # It gives up rather than waiting, so the beat schedule cannot pile workers up on one election
    assert file_count == 0
    assert imported_batches == []
    assert ImportedCommit.objects.count() == 0
    # Returning 0 is indistinguishable from an election with nothing left to import,
    # so the warning is the only trace the skipped run leaves behind
    assert warnings_of(caplog) == [
        f"Could not acquire lock, GithubEmlFileHandler is already running for {stored_election_config.identifier}"
    ]


def test_run_locks_per_election_and_not_globally(fake_repo, imported_batches, stored_election_config, caplog):
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    other_election = GithubEmlFileHandler(ElectionConfigFactory.build(identifier="OTHER2026"))

    # An import running for a different election must not hold this one up
    with cache.lock(other_election.cache_lock_key, timeout=LOCK_TIMEOUT):
        file_count = GithubEmlFileHandler(stored_election_config).run()

    assert file_count == 1
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]
    assert warnings_of(caplog) == []


def test_run_releases_the_lock_when_it_finishes(fake_repo, imported_batches, stored_election_config):
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    importer = GithubEmlFileHandler(stored_election_config)

    importer.run()

    assert cache.lock(importer.cache_lock_key, blocking=False).acquire() is True


def test_run_holds_a_lock_that_expires_on_its_own(fake_repo, monkeypatch, stored_election_config):
    """A worker that dies mid-import must not block its election forever."""
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    importer = GithubEmlFileHandler(stored_election_config)
    remaining = []

    def observe_ttl(self, files):
        remaining.append(cache.ttl(importer.cache_lock_key))

    monkeypatch.setattr(GithubEmlFileHandler, "import_file_objects", observe_ttl)

    importer.run()

    assert remaining == [LOCK_TIMEOUT]


def test_run_keeps_its_result_when_the_lock_expires_mid_import(fake_repo, monkeypatch, stored_election_config, caplog):
    fake_repo(commits=[FakeCommit("first", [FakeFile("telling.xml")])], contents={"telling.xml": XML_510B})
    importer = GithubEmlFileHandler(stored_election_config)

    def expire_lock(self, files):
        # As if LOCK_TIMEOUT elapsed while this import was still running
        cache.delete(importer.cache_lock_key)

    monkeypatch.setattr(GithubEmlFileHandler, "import_file_objects", expire_lock)

    file_count = importer.run()

    # Releasing an expired lock fails, but the import itself ran to completion,
    # so its result and its bookkeeping stand rather than being reported as a skipped run
    assert file_count == 1
    assert list(ImportedCommit.objects.values_list("branch_type", "commit_sha")) == [(BranchType.EXCHANGE, "first")]
    # Renew fails mid-run, then the outer release also reports expiry
    assert warnings_of(caplog) == [
        f"Lock for {stored_election_config.identifier} expired while importing commits",
        f"Lock for {stored_election_config.identifier} expired before the import finished",
    ]
