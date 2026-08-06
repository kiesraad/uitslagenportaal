import base64
import io
import itertools
import logging
import zipfile
from typing import Iterator

from django.conf import settings
from github import Auth, Github
from github.File import File

from election.models import ElectionConfig
from eml_import.models import BranchType, ImportedCommit
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.election_importer import ElectionImporter

COMMIT_BATCH_SIZE = 25

# The branches to import, in import order, mapped to the ElectionConfig field holding the branch name
BRANCH_FIELDS: dict[BranchType, str] = {
    BranchType.EXCHANGE: "gh_exchange_branch",
    BranchType.COUNTING_RESULTS: "gh_counting_results_branch",
}


class GithubEmlImporter:
    def __init__(self, election_config: ElectionConfig) -> None:
        self.election_config = election_config
        self.gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN), per_page=500)
        self.repo = self.gh.get_repo(settings.GITHUB_INGRESS_REPO)
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> int:
        """
        Import the next batch of commits from the first branch that still has commits left.
        :return: the number of imported files
        """
        for branch_type, branch in self._iterate_branches():
            last_imported = (
                ImportedCommit.objects.filter(election_config=self.election_config, branch_type=branch_type)
                .order_by("-created_at")
                .first()
            )
            self.logger.info(
                "Starting GitHub importer for election %s",
                self.election_config.identifier,
            )

            self.logger.info(
                "Fetching files for next batch of commits on branch %s at %s...",
                branch,
                last_imported.commit_sha if last_imported else "first commit",
            )
            batch_head_sha, files = self._get_next_batch_of_files(
                last_imported.commit_sha if last_imported else None, branch
            )
            # This branch is fully imported, so continue with the next one
            if batch_head_sha is None:
                self.logger.info(
                    "No commits remaining on %s branch (%s)",
                    branch_type,
                    branch,
                )
                continue

            xml_files = list(self._iterate_all_xml_files(files))
            ElectionImporter().import_files(xml_files)
            ImportedCommit.objects.create(
                election_config=self.election_config,
                branch_type=branch_type,
                commit_sha=batch_head_sha,
            )

            return len(xml_files)

        return 0

    def _iterate_branches(self) -> Iterator[tuple[BranchType, str]]:
        """
        Iterate the configured branches of the election config, in import order.
        :return:
        """
        for branch_type, field in BRANCH_FIELDS.items():
            branch = getattr(self.election_config, field)
            if branch:
                yield branch_type, branch

            else:
                self.logger.info("No %s branch configured for %s", branch_type, self.election_config.identifier)

    def _get_next_batch_of_files(self, base_sha: str | None, branch: str) -> tuple[str | None, list[File]]:
        if base_sha is not None:
            # Get the commits ahead of the base_sha ref, so commits[0] is the first commit after base_Sha
            ahead = self.repo.compare(base_sha, branch)
            commits = list(itertools.islice(ahead.commits, COMMIT_BATCH_SIZE))
        else:
            # Get the first commits of the branch, so commits[0] is the first ever commit
            commits = list(itertools.islice(self.repo.get_commits(sha=branch).reversed, COMMIT_BATCH_SIZE))

        if not commits:
            return None, []

        batch_head_sha = commits[-1].sha

        # Compare does not return the files in the commit of the given sha,
        # so get the files of the first commit separately
        files = list(self.repo.get_commit(commits[0].sha).files)
        if len(commits) == 1:
            return batch_head_sha, files

        # Try to get the files using a diff, which works up to 300 files and is enough most of the time
        diff_files = self.repo.compare(commits[0].sha, batch_head_sha).files
        if len(diff_files) < 300:
            return batch_head_sha, files + diff_files

        # Get files per commit instead, because we have 300 or more changed files.
        # This costs at least one extra request per commit
        self.logger.info("Fetch files for each commit, >= 300 files found...")
        for commit in commits[1:]:
            files += list(self.repo.get_commit(commit.sha).files)

        return batch_head_sha, files

    def _iterate_all_xml_files(self, files: list[File]) -> Iterator[NamedBytesIO]:
        """
        Iterate all XML files, including the ones from zip files.
        :param files:
        :return:
        """
        for file in files:
            # Possible file statuses: added, removed, modified, renamed, copied, changed, unchanged
            if file.filename.split(".")[-1] not in ["xml", "zip"] or file.status in ["removed", "unchanged"]:
                self.logger.info("Skipping %s (%s)", file.filename, file.status)
                continue

            self.logger.info("Downloading %s (sha: %s)", file.filename, file.sha)
            content = base64.b64decode(self.repo.get_git_blob(file.sha).content)

            # Unzip any zip file and iterate its content
            if file.filename.endswith(".zip"):
                for extracted_file in self._iterate_zip(content):
                    yield extracted_file

            # Yield any xml file directly
            if file.filename.endswith(".xml"):
                yield NamedBytesIO(content, file.filename)

    def _iterate_zip(self, content: bytes) -> Iterator[NamedBytesIO]:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if name.endswith(".zip"):
                    for file in self._iterate_zip(zf.read(name)):
                        yield file

                if name.endswith(".xml"):
                    yield NamedBytesIO(zf.read(name), name)
