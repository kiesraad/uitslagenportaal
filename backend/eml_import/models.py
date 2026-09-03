import hashlib
from io import BytesIO
from pathlib import Path

from django.db import models

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
    """Exact-byte duplicate of an EML already imported successfully; skip it."""

    sha256 = models.CharField(max_length=64, unique=True)

    @staticmethod
    def _sha256(eml_file: Path | BytesIO) -> str:
        data = eml_file.read_bytes() if isinstance(eml_file, Path) else eml_file.getvalue()
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def already_imported(cls, eml_file: Path | BytesIO) -> bool:
        return cls.objects.filter(sha256=cls._sha256(eml_file)).exists()

    @classmethod
    def record(cls, eml_file: Path | BytesIO) -> None:
        cls.objects.get_or_create(sha256=cls._sha256(eml_file))
