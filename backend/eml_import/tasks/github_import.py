import itertools

from django.conf import settings
from github import Auth, Github
from github.ContentFile import ContentFile
from github.File import File
from github.Repository import Repository

from eml_import.models import ImportedCommit
from mainsite.utils.election_importer import ElectionImporter

COMMIT_BATCH_SIZE = 1


def _get_repo() -> Repository:
    gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
    test = gh.get_user().get_repos()
    return gh.get_repo(settings.GITHUB_INGRESS_REPO)


def _bootstrap_batch(repo: Repository) -> tuple[str | None, list[File]]:
    # No stored ref yet, and the root commit has no parent to compare() against.
    commits = list(itertools.islice(repo.get_commits(sha=settings.GITHUB_INGRESS_BRANCH).reversed, COMMIT_BATCH_SIZE))
    if not commits:
        return None, []

    batch_head_sha = commits[-1].sha
    files = list(repo.get_commit(commits[0].sha).files)
    if len(commits) > 1:
        files += repo.compare(commits[0].sha, batch_head_sha).files

    return batch_head_sha, files


def _next_batch(repo: Repository, base_sha: str) -> tuple[str | None, list[File]]:
    ahead = repo.compare(base_sha, settings.GITHUB_INGRESS_BRANCH)
    commits = list(itertools.islice(ahead.commits, COMMIT_BATCH_SIZE))
    if not commits:
        return None, []

    batch_head_sha = commits[-1].sha
    files = list(repo.compare(base_sha, batch_head_sha).files)

    return batch_head_sha, files


def _fetch_file_content(repo: Repository, file: File, ref: str) -> bytes:
    content: ContentFile = repo.get_contents(file.filename, ref=ref)
    return content.decoded_content


def import_next_eml_commit() -> int:
    repo = _get_repo()
    last_imported = ImportedCommit.objects.order_by("-created_at").first()

    if last_imported is None:
        batch_head_sha, files = _bootstrap_batch(repo)
    else:
        batch_head_sha, files = _next_batch(repo, last_imported.commit_sha)

    if batch_head_sha is None:
        return 0

    for file in files:
        if file.status == "removed" or not file.filename.endswith(".xlm"):
            continue

        ElectionImporter.import_single(
            _fetch_file_content(repo, file, batch_head_sha)
        )

    ImportedCommit.objects.create(commit_sha=batch_head_sha)

    return len(files)
