import itertools
import logging

from django.conf import settings
from github import Auth, Github
from github.ContentFile import ContentFile
from github.File import File

from eml_import.models import ImportedCommit
from mainsite.utils.election_importer import ElectionImporter

COMMIT_BATCH_SIZE = 5


class GithubEmlImporter:
    def __init__(self) -> None:
        self.gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
        self.repo = self.gh.get_repo(settings.GITHUB_INGRESS_REPO)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _bootstrap_batch(self) -> tuple[str | None, list[File]]:
        # No stored ref yet, and the root commit has no parent to compare() against.
        commits = list(
            itertools.islice(self.repo.get_commits(sha=settings.GITHUB_INGRESS_BRANCH).reversed, COMMIT_BATCH_SIZE)
        )
        if not commits:
            return None, []

        batch_head_sha = commits[-1].sha
        files = list(self.repo.get_commit(commits[0].sha).files)
        if len(commits) > 1:
            files += self.repo.compare(commits[0].sha, batch_head_sha).files

        return batch_head_sha, files

    def _next_batch(self, base_sha: str) -> tuple[str | None, list[File]]:
        ahead = self.repo.compare(base_sha, settings.GITHUB_INGRESS_BRANCH)
        commits = list(itertools.islice(ahead.commits, COMMIT_BATCH_SIZE))
        if not commits:
            return None, []

        batch_head_sha = commits[-1].sha
        files = list(self.repo.compare(base_sha, batch_head_sha).files)

        return batch_head_sha, files

    def _fetch_file_content(self, file: File, ref: str) -> bytes:
        content: ContentFile = self.repo.get_contents(file.filename, ref=ref)
        return content.decoded_content

    def run(self) -> int:
        last_imported = ImportedCommit.objects.order_by("-created_at").first()
        self.logger.info("Starting GitHub importer at next commit after %s", last_imported)

        if last_imported is None:
            batch_head_sha, files = self._bootstrap_batch()
        else:
            batch_head_sha, files = self._next_batch(last_imported.commit_sha)

        if batch_head_sha is None:
            return 0

        file_cnt = 0
        for file in files:
            if file.status == "removed" or not file.filename.endswith(".xlm"):
                self.logger.info("Skipping import of %s (%s)", file.filename, file.status)
                continue

            self.logger.info("Processing %s...")
            file_cnt += 1
            ElectionImporter.import_single(self._fetch_file_content(file, batch_head_sha))

        ImportedCommit.objects.create(commit_sha=batch_head_sha)

        return file_cnt
