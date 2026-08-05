import io
import itertools
import logging
import zipfile
from typing import Iterator

from django.conf import settings
from github import Auth, Github
from github.ContentFile import ContentFile
from github.File import File

from eml_import.models import ImportedCommit
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.election_importer import ElectionImporter

COMMIT_BATCH_SIZE = 10


class GithubEmlImporter:
    def __init__(self) -> None:
        self.gh = Github(auth=Auth.Token(settings.GITHUB_TOKEN))
        self.repo = self.gh.get_repo(settings.GITHUB_INGRESS_REPO)
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> int:
        last_imported = ImportedCommit.objects.order_by("-created_at").first()
        self.logger.info(
            "Starting GitHub importer at %s",
            last_imported.commit_sha if last_imported else "first commit",
        )

        batch_head_sha, files = self._get_next_batch_of_files(last_imported.commit_sha if last_imported else None)
        if batch_head_sha is None:
            return 0

        files = list(self._iterate_all_xml_files(files, batch_head_sha))
        ElectionImporter().import_files(files)
        ImportedCommit.objects.create(commit_sha=batch_head_sha)

        return len(files)

    def _get_next_batch_of_files(self, base_sha: str | None) -> tuple[str | None, list[File]]:
        if base_sha is not None:
            # Get the commits ahead of the base_sha ref, so commits[0] is the first commit after base_Sha
            ahead = self.repo.compare(base_sha, settings.GITHUB_INGRESS_BRANCH)
            commits = list(itertools.islice(ahead.commits, COMMIT_BATCH_SIZE))
        else:
            # Get the first commits of the repo, so commits[0] is the first ever commit
            commits = list(
                itertools.islice(self.repo.get_commits(sha=settings.GITHUB_INGRESS_BRANCH).reversed, COMMIT_BATCH_SIZE)
            )

        if not commits:
            return None, []

        # Compare does not return the files in the commit of the given sha,
        # so get the files of the first commit separately
        batch_head_sha = commits[-1].sha
        files = list(self.repo.get_commit(commits[0].sha).files)
        if len(commits) > 1:
            files += self.repo.compare(commits[0].sha, batch_head_sha).files

        return batch_head_sha, files

    def _iterate_all_xml_files(self, files: list[File], ref: str) -> Iterator[NamedBytesIO]:
        """
        Iterate all XML files, including the ones from zip files.
        :param files:
        :param ref:
        :return:
        """
        for file in files:
            # Possible file statuses: added, removed, modified, renamed, copied, changed, unchanged
            if file.filename.split(".")[-1] not in ["xml", "zip"] or file.status in ["removed", "unchanged"]:
                self.logger.info("Skipping %s (%s)", file.filename, file.status)
                continue

            content: ContentFile = self.repo.get_contents(file.filename, ref=ref)

            # Unzip any zip file and iterate its content
            if file.filename.endswith(".zip"):
                for extracted_file in self._iterate_zip(content.decoded_content):
                    yield extracted_file

            # Yield any xml file directly
            if file.filename.endswith(".xml"):
                yield NamedBytesIO(content.decoded_content, file.filename)

    def _iterate_zip(self, content: bytes) -> Iterator[NamedBytesIO]:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if name.endswith(".zip"):
                    for file in self._iterate_zip(zf.read(name)):
                        yield file

                if name.endswith(".xml"):
                    yield NamedBytesIO(zf.read(name), name)
