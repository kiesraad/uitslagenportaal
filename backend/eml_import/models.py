import hashlib
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

from django.db import models

from election.models import Election
from eml_import.exceptions import FileAlreadyImported
from mainsite.models import BaseModel


class BranchType(models.TextChoices):
    EXCHANGE = "exchange", "Exchange"  # ElectionConfig.gh_exchange_branch
    COUNTING_RESULTS = "counting_results", "Counting results"  # ElectionConfig.gh_counting_results_branch


class ImportedCommit(BaseModel):
    election_config = models.ForeignKey(
        "election.ElectionConfig",
        on_delete=models.CASCADE,
        related_name="imported_commits",
    )
    # The branch name itself lives on the ElectionConfig, so it can change without losing progress
    branch_type = models.CharField(max_length=32, choices=BranchType.choices)
    commit_sha = models.CharField(max_length=40)


class ImportedEmlHash(BaseModel):
    """To record imported EML files based on a sha256 file hash"""

    election = models.ForeignKey(
        "election.Election",
        on_delete=models.CASCADE,
        related_name="+",
    )
    sha256 = models.CharField(max_length=64, unique=True)

    @staticmethod
    def _sha256(eml_file: Path | BytesIO) -> str:
        data = eml_file.read_bytes() if isinstance(eml_file, Path) else eml_file.getvalue()
        return hashlib.sha256(data).hexdigest()

    @classmethod
    @contextmanager
    def if_not_imported(cls, eml_file: Path | BytesIO, election: Election):
        """Run the block unless these bytes were imported before; record them once it succeeds."""
        sha256 = cls._sha256(eml_file)
        if cls.objects.filter(sha256=sha256).exists():
            raise FileAlreadyImported()

        yield
        cls.objects.get_or_create(sha256=sha256, defaults={"election": election})
