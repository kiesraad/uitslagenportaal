import io
import zipfile
from datetime import timedelta

import pytest
from django.utils import timezone

from eml_import.models import ImportedCommit
from eml_import.tests.factories import ImportedCommitFactory
from eml_import.tests.fakes import FakeCommit, FakeFile, FakeGithub, FakeRepo
from eml_import.utils import github_eml_importer
from eml_import.utils.github_eml_importer import COMMIT_BATCH_SIZE, GithubEmlImporter

XML_110A = b"<EML Id='110a'/>"
XML_230B = b"<EML Id='230b'/>"
XML_510B = b"<EML Id='510b'/>"


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
    """Build a FakeRepo and make GithubEmlImporter construct itself against it."""
    settings.GITHUB_TOKEN = "token"  # Auth.Token rejects None, and the setting is unset in CI
    settings.GITHUB_INGRESS_REPO = "owner/repo"
    settings.GITHUB_INGRESS_BRANCH = "main"

    def build(commits, contents=None):
        repo = FakeRepo(commits, contents)
        monkeypatch.setattr(github_eml_importer, "Github", lambda auth: FakeGithub(repo))
        return repo

    return build


@pytest.fixture
def imported_batches(monkeypatch):
    """Capture what run() hands to ElectionImporter, without parsing any real EML."""
    batches = []

    class RecordingElectionImporter:
        def import_files(self, files):
            batches.append(files)

    monkeypatch.setattr(github_eml_importer, "ElectionImporter", RecordingElectionImporter)
    return batches


def test_iterate_all_xml_files_yields_xml_and_unpacks_zip(fake_repo):
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

    extracted = list(GithubEmlImporter()._iterate_all_xml_files(files, "head"))

    assert as_pairs(extracted) == [
        ("results/telling.xml", XML_510B),
        ("inner/kandidaten.xml", XML_230B),
    ]
    # Files with an unsupported extension are never fetched, and everything is read
    # at the batch head ref
    assert repo.calls_named("get_contents") == [
        ("get_contents", "results/telling.xml", "head"),
        ("get_contents", "results/bundle.zip", "head"),
    ]


@pytest.mark.parametrize("status", ["added", "modified", "renamed", "copied", "changed"])
def test_iterate_all_xml_files_imports_every_status_that_leaves_a_file_behind(fake_repo, status):
    fake_repo(commits=[FakeCommit("head")], contents={"telling.xml": XML_510B})

    extracted = list(GithubEmlImporter()._iterate_all_xml_files([FakeFile("telling.xml", status)], "head"))

    assert as_pairs(extracted) == [("telling.xml", XML_510B)]


@pytest.mark.parametrize("status", ["removed", "unchanged"])
def test_iterate_all_xml_files_skips_removed_and_unchanged(fake_repo, status):
    repo = fake_repo(commits=[FakeCommit("head")], contents={"telling.xml": XML_510B})

    extracted = list(GithubEmlImporter()._iterate_all_xml_files([FakeFile("telling.xml", status)], "head"))

    assert extracted == []
    assert repo.calls_named("get_contents") == []


def test_iterate_all_xml_files_unpacks_nested_zip(fake_repo):
    inner = zip_bytes({"telling.xml": XML_510B})
    fake_repo(
        commits=[FakeCommit("head")],
        contents={"outer.zip": zip_bytes({"nested/inner.zip": inner})},
    )

    extracted = list(GithubEmlImporter()._iterate_all_xml_files([FakeFile("outer.zip")], "head"))

    # Named after the entry inside the archive, not after the zip it arrived in
    assert as_pairs(extracted) == [("telling.xml", XML_510B)]


def test_get_next_batch_of_files_starts_at_the_oldest_commit(fake_repo):
    repo = fake_repo(
        commits=[
            FakeCommit("oldest", [FakeFile("a.xml")]),
            FakeCommit("middle", [FakeFile("b.xml")]),
            FakeCommit("newest", [FakeFile("c.xml")]),
        ]
    )

    head_sha, files = GithubEmlImporter()._get_next_batch_of_files(None)

    assert head_sha == "newest"
    # compare() excludes the base commit, so the oldest commit is fetched separately;
    # the two sources must not overlap
    assert [file.filename for file in files] == ["a.xml", "b.xml", "c.xml"]
    assert repo.calls_named("get_commits") == [("get_commits", "main")]
    assert repo.calls_named("get_commit") == [("get_commit", "oldest")]
    assert repo.calls_named("compare") == [("compare", "oldest", "newest")]


def test_get_next_batch_of_files_caps_the_batch_size(fake_repo):
    commits = [FakeCommit(f"c{index}", [FakeFile(f"{index}.xml")]) for index in range(COMMIT_BATCH_SIZE + 2)]
    fake_repo(commits=commits)

    head_sha, files = GithubEmlImporter()._get_next_batch_of_files(None)

    assert head_sha == f"c{COMMIT_BATCH_SIZE - 1}"
    assert len(files) == COMMIT_BATCH_SIZE


def test_get_next_batch_of_files_resumes_after_the_base_commit(fake_repo):
    repo = fake_repo(
        commits=[
            FakeCommit("imported", [FakeFile("already-done.xml")]),
            FakeCommit("next", [FakeFile("a.xml")]),
            FakeCommit("last", [FakeFile("b.xml")]),
        ]
    )

    head_sha, files = GithubEmlImporter()._get_next_batch_of_files("imported")

    assert head_sha == "last"
    # The base commit's own files are not imported a second time
    assert [file.filename for file in files] == ["a.xml", "b.xml"]
    assert repo.calls_named("compare")[0] == ("compare", "imported", "main")


def test_get_next_batch_of_files_returns_nothing_when_up_to_date(fake_repo):
    repo = fake_repo(commits=[FakeCommit("imported", [FakeFile("a.xml")])])

    head_sha, files = GithubEmlImporter()._get_next_batch_of_files("imported")

    assert head_sha is None
    assert files == []
    # Bails out before fetching any files
    assert repo.calls_named("get_commit") == []
    assert repo.calls_named("compare") == [("compare", "imported", "main")]


def test_get_next_batch_of_files_does_not_diff_a_single_commit(fake_repo):
    repo = fake_repo(
        commits=[
            FakeCommit("imported", [FakeFile("already-done.xml")]),
            FakeCommit("only", [FakeFile("a.xml")]),
        ]
    )

    head_sha, files = GithubEmlImporter()._get_next_batch_of_files("imported")

    assert head_sha == "only"
    assert [file.filename for file in files] == ["a.xml"]
    # compare() is only used to list the commits; the files come from get_commit()
    assert repo.calls_named("compare") == [("compare", "imported", "main")]
    assert repo.calls_named("get_commit") == [("get_commit", "only")]


@pytest.mark.django_db
def test_run_imports_from_the_first_commit_and_records_progress(fake_repo, imported_batches):
    fake_repo(
        commits=[
            FakeCommit("first", [FakeFile("verkiezingsdefinitie.xml")]),
            FakeCommit("second", [FakeFile("kandidatenlijst.xml")]),
        ],
        contents={"verkiezingsdefinitie.xml": XML_110A, "kandidatenlijst.xml": XML_230B},
    )

    file_count = GithubEmlImporter().run()

    assert file_count == 2
    assert as_pairs(imported_batches[0]) == [
        ("verkiezingsdefinitie.xml", XML_110A),
        ("kandidatenlijst.xml", XML_230B),
    ]
    assert list(ImportedCommit.objects.values_list("commit_sha", flat=True)) == ["second"]


@pytest.mark.django_db
def test_run_resumes_from_the_most_recently_imported_commit(fake_repo, imported_batches):
    repo = fake_repo(
        commits=[FakeCommit("recent"), FakeCommit("new", [FakeFile("telling.xml")])],
        contents={"telling.xml": XML_510B},
    )
    ImportedCommitFactory(commit_sha="recent")
    stale = ImportedCommitFactory(commit_sha="stale")
    # created_at is auto_now_add, so age it afterwards to make insertion order
    # deliberately disagree with created_at order
    ImportedCommit.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(days=1))

    GithubEmlImporter().run()

    assert repo.calls_named("compare")[0] == ("compare", "recent", "main")
    assert as_pairs(imported_batches[0]) == [("telling.xml", XML_510B)]


@pytest.mark.django_db
def test_run_does_nothing_when_there_are_no_new_commits(fake_repo, imported_batches):
    fake_repo(commits=[FakeCommit("imported", [FakeFile("a.xml")])])
    ImportedCommitFactory(commit_sha="imported")

    file_count = GithubEmlImporter().run()

    assert file_count == 0
    assert imported_batches == []
    assert ImportedCommit.objects.count() == 1
