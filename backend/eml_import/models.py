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
