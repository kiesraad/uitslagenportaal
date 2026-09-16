import base64
import io
import itertools
import logging
import zipfile
from typing import Iterator

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from github import Auth, Github
from github.File import File
from github.Repository import Repository
from redis.exceptions import LockError

from election.models import ElectionConfig
from eml_import.exceptions import EMLImporterException, GithubImportException
from eml_import.models import BranchType, ImportedCommit
from eml_import.utils.file_handler import BaseFileHandler
from eml_import.utils.named_bytes_io import NamedBytesIO

# Seconds before the per-election lock expires on its own, so a worker that dies
# mid-import does not block that election forever. Acquired afresh for each commit.
LOCK_TIMEOUT = 20 * 60

# The branches to import, in import order, mapped to the ElectionConfig field holding the branch name
BRANCH_FIELDS: dict[BranchType, str] = {
    BranchType.EXCHANGE: "gh_exchange_branch",
    BranchType.COUNTING_RESULTS: "gh_counting_results_branch",
}


class GithubEmlFileHandler(BaseFileHandler):
    def __init__(self, election_config: ElectionConfig) -> None:
        super().__init__()
        self.election_config = election_config
        self.gh: Github | None = None
        self.repo: Repository | None = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{self.election_config.identifier}]")

    @property
    def cache_lock_key(self):
        return f"github-eml-importer:{self.election_config.identifier.lower()}"

    def run(self) -> tuple[int, bool]:
        self.logger.info(
            "Starting GitHub importer for election %s",
            self.election_config.identifier,
        )

        if not settings.GITHUB_TOKEN or not settings.GITHUB_INGRESS_REPO:
            raise GithubImportException("GITHUB_TOKEN and/or GITHUB_INGRESS_REPO not configured.")

        self.gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
        self.repo = self.gh.get_repo(settings.GITHUB_INGRESS_REPO)

        # One import per election at a time, so two workers cannot import the same commits twice
        lock = cache.lock(self.cache_lock_key, timeout=LOCK_TIMEOUT, blocking=False)
        if not lock.acquire():
            self.logger.warning(
                "Could not acquire lock, GithubEmlFileHandler is already running for %s",
                self.election_config.identifier,
            )
            # No files are processed and set remaining commits to False, so no follow-up task is scheduled
            return 0, False

        try:
            return self._run_import()
        finally:
            try:
                lock.release()
            except LockError:
                self.logger.warning(
                    "Lock for %s expired while importing commits",
                    self.election_config.identifier,
                )

    def _run_import(self) -> tuple[int, bool]:
        """
        Import the next commit.
        :return: Tuple of [the number of imported files, if commits remain to be processed]
        """
        imported_files, commits_remaining = 0, False

        branches = list(self._iterate_branches())
        for index, (branch_type, branch) in enumerate(branches):
            last_imported = (
                ImportedCommit.objects.filter(election_config=self.election_config, branch_type=branch_type)
                .order_by("-created_at")
                .first()
            )

            next_commit_sha, files, commits_remaining = self._get_files_for_next_commit(
                last_imported.commit_sha if last_imported else None, branch
            )
            self.logger.info(
                "Fetched files for next commit on branch %s at %s: %s",
                branch,
                last_imported.commit_sha if last_imported else "first commit",
                f"{len(files)} files" if next_commit_sha else "no commits remaining",
            )
            if next_commit_sha is None:
                continue

            xml_files = list(self._iterate_all_xml_files(files))
            self.import_file_objects(xml_files)
            ImportedCommit.objects.create(
                election_config=self.election_config,
                branch_type=branch_type,
                commit_sha=next_commit_sha,
            )
            imported_files += len(xml_files)

            # A later branch may still hold commits even when this one is caught up
            return imported_files, commits_remaining or index < len(branches) - 1

        # We reach this only if all commits are processed
        return imported_files, False

    def import_file_objects(self, files: list[NamedBytesIO]) -> None:
        """
        Import all given file-like objects.
        """
        xml_files = self._classify_files(files)
        for parser_type, (binding, importer_cls) in self._DOCUMENT_TYPES.items():
            for file in xml_files[parser_type]:
                self.logger.info(f"Importing {parser_type} file {file.filename}")
                eml = self._parser.from_bytes(file.getvalue(), binding)
                try:
                    with transaction.atomic():
                        importer_cls(eml, file).parse()
                except EMLImporterException as e:
                    # Let other exceptions (like DB connection issues) bubble up so they are not silenced
                    self.logger.error(
                        f"\033[31mFailed importing {parser_type} file {file.filename} "
                        f"with exception: {type(e).__name__} {e}\033[0m"
                    )

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

    def _get_files_for_next_commit(self, base_sha: str | None, branch: str) -> tuple[str | None, list[File], bool]:
        """
        :return: A tuple of [the head sha, list of files, if there are remaining commits]
        """
        if base_sha is not None:
            # Get the commits ahead of the base_sha ref, so commits[0] is the first commit after base_Sha
            ahead = self.repo.compare(base_sha, branch)
            commits = list(itertools.islice(ahead.commits, 2))
        else:
            # Get the first commits of the branch, so commits[0] is the first ever commit
            commits = list(itertools.islice(self.repo.get_commits(sha=branch).reversed, 2))

        if not commits:
            return None, [], False

        commit = commits[0]
        files = list(self.repo.get_commit(commit.sha).files)

        return commit.sha, files, len(commits) > 1

    @staticmethod
    def _is_eml_ingress_file(filename: str) -> bool:
        extension = filename.rsplit(".", 1)[-1].lower()
        return extension in ("xml", "zip")

    def _log_eml_removals_without_additions(self, files: list[File]) -> None:
        """
        Log when a removed zip/xml is not superseded by a new upload in the same folder.

        The overdrachtsplatform replaces an upload by deleting the old zip and adding a
        corrected one in the same commit; only removals do not occur. This log is here
        to log in case this does happen.
        """
        folders_with_adds = {
            file.filename.rsplit("/", 1)[0]
            for file in files
            if file.status == "added" and self._is_eml_ingress_file(file.filename)
        }
        for file in files:
            if file.status == "removed" and self._is_eml_ingress_file(file.filename):
                folder = file.filename.rsplit("/", 1)[0]
                if folder not in folders_with_adds:
                    self.logger.error(
                        "EML file removed without a replacement in the same commit; deletion was not processed: %s",
                        file.filename,
                    )

    def _iterate_all_xml_files(self, files: list[File]) -> Iterator[NamedBytesIO]:
        """
        Iterate all XML files, including the ones from zip files.
        :param files:
        :return:
        """
        self._log_eml_removals_without_additions(files)

        for file in files:
            # Possible file statuses: added, removed, modified, renamed, copied, changed, unchanged.
            # Removals are swaps (old zip deleted, corrected zip added in the
            # same commit), not removals — safe to skip. Unpaired removals are
            # logged as errors above.
            if not self._is_eml_ingress_file(file.filename) or file.status in ["removed", "unchanged"]:
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
