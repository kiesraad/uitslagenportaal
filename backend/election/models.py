from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import models

from mainsite.models import BaseModel
from mainsite.utils.utils import name_to_slug


class ElectionConfig(BaseModel):
    identifier = models.CharField(max_length=64, unique=True)
    category = models.CharField(max_length=2)
    label = models.CharField(max_length=255, default="")
    slug = models.SlugField(unique=True, db_index=True)
    date = models.DateTimeField()
    issue_report_opens_at = models.DateTimeField(
        default=datetime(2026, 12, 8, 9, 0, tzinfo=ZoneInfo("Europe/Amsterdam")),
    )
    issue_report_deadline = models.DateTimeField(
        default=datetime(2026, 12, 14, 10, 0, tzinfo=ZoneInfo("Europe/Amsterdam")),
    )
    report_error_url = models.URLField(max_length=500, blank=True, default="")
    counting_info_url = models.URLField(max_length=500, blank=True, default="")
    voting_url = models.URLField(max_length=500, blank=True, default="")
    gh_counting_results_branch = models.CharField(max_length=255, null=True)
    gh_exchange_branch = models.CharField(max_length=255, null=True)

    @property
    def csb_type(self):
        return self.elections.first().regions.first().region_category

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = name_to_slug(self.identifier)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.identifier


class Election(BaseModel):
    name = models.CharField(max_length=255)
    subcategory = models.CharField(max_length=8)
    date = models.DateField()
    slug = models.CharField(max_length=64, unique=True, db_index=True)
    election_config = models.ForeignKey(
        "election.ElectionConfig",
        on_delete=models.CASCADE,
        related_name="elections",
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = name_to_slug(self.name)[:49]
        super().save(*args, **kwargs)


class TimelineEntryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in-progress", "In progress"
    DONE = "done", "Done"


class TimelineVariant(models.TextChoices):
    CSO = "CSO", "Centrale Stemopname"
    DSO = "DSO", "Decentrale Stemopname"
    DEFAULT = "DEFAULT", "Default"


class TimelineEntry(BaseModel):
    election_config = models.ForeignKey(
        "election.ElectionConfig",
        on_delete=models.CASCADE,
        related_name="timeline_entries",
    )
    variant = models.CharField(
        max_length=8,
        choices=TimelineVariant.choices,
        default=TimelineVariant.DEFAULT,
    )
    status = models.CharField(max_length=16, choices=TimelineEntryStatus.choices)
    title = models.CharField(max_length=255)
    date = models.DateTimeField()
    body = models.TextField()

    class Meta:
        # Entries are ordered chronologically by date.
        ordering = ("date",)

    def __str__(self):
        return f"{self.election_config.identifier} [{self.variant}]: {self.title}"


class Contest(BaseModel):
    identifier = models.CharField(max_length=255, blank=True)
    election = models.ForeignKey(
        "election.Election",
        on_delete=models.CASCADE,
        related_name="contests",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["election", "identifier"],
                name="unique_contest_identifier_per_election",
            )
        ]


class EMLTypeMixin(models.Model):
    class Meta:
        abstract = True

    EML_TYPE_510B = "510b"
    EML_TYPE_510D = "510d"
    EML_TYPE_CHOICES = [
        (EML_TYPE_510B, "510b"),
        (EML_TYPE_510D, "510d"),
    ]
    eml_type = models.CharField(max_length=32, choices=EML_TYPE_CHOICES, null=True)


class VoteCount(EMLTypeMixin, BaseModel):
    contest = models.ForeignKey(
        "election.Contest",
        on_delete=models.CASCADE,
        related_name="vote_counts",
    )
    region = models.ForeignKey(
        "region.Region",
        on_delete=models.CASCADE,
        related_name="vote_counts",
    )
    party = models.ForeignKey(
        "party.Party",
        on_delete=models.CASCADE,
        related_name="vote_counts",
    )
    candidate = models.ForeignKey(
        "party.Candidate",
        on_delete=models.CASCADE,
        related_name="vote_counts",
        null=True,
        blank=True,
    )
    valid_votes = models.PositiveIntegerField()

    RESULT_LEVEL_PARTY = "PARTY"
    RESULT_LEVEL_CANDIDATE = "CANDIDATE"
    RESULT_LEVEL_CHOICES = [
        (RESULT_LEVEL_PARTY, "Party"),
        (RESULT_LEVEL_CANDIDATE, "Candidate"),
    ]
    result_level = models.CharField(
        max_length=32,
        choices=RESULT_LEVEL_CHOICES,
        default=RESULT_LEVEL_CANDIDATE,
    )

    # TODO: create unique contstraint
    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=["contest", "region", "party", "candidate"],
    #             name="unique_vote_count_per_contest_region_party_candidate",
    #         )
    #     ]


class ElectionDocument(BaseModel):
    region = models.ForeignKey(
        "region.Region",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    storage_key = models.CharField(max_length=512, unique=True)
    content_type = models.CharField(max_length=128, default="application/xml")
    size = models.PositiveIntegerField()
    FILE_TYPE_EML510B = "EML510b"
    FILE_TYPE_CHOICES = [
        (FILE_TYPE_EML510B, "EML510b"),
    ]
    file_type = models.CharField(
        max_length=32,
        choices=FILE_TYPE_CHOICES,
        default=FILE_TYPE_EML510B,
        help_text="Type of the election document",
    )


class VoterTurnoutCount(EMLTypeMixin, BaseModel):
    contest = models.ForeignKey(
        "election.Contest",
        on_delete=models.CASCADE,
        related_name="voter_turnout_counts",
    )
    region = models.ForeignKey(
        "region.Region",
        on_delete=models.CASCADE,
        related_name="voter_turnout_counts",
    )

    CATEGORY_REJECTED = "REJECTED"
    CATEGORY_UNCOUNTED = "UNCOUNTED"
    CATEGORY_TOTALS = "TOTALS"
    CATEGORY_CHOICES = [
        (CATEGORY_REJECTED, "Rejected votes"),
        (CATEGORY_UNCOUNTED, "Uncounted votes"),
        (CATEGORY_TOTALS, "Total votes"),
    ]
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES)
    reason_code = models.CharField(max_length=64)
    votes = models.PositiveIntegerField()
