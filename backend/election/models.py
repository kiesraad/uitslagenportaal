from dataclasses import dataclass
from datetime import datetime
from typing import Self
from zoneinfo import ZoneInfo

from django.db import models
from django.db.models import Q
from django.db.models.enums import Choices

from election.utils import visibility_cutoff
from mainsite.models import BaseModel, RegionCategory
from mainsite.utils.eml_type import EmlType
from mainsite.utils.utils import name_to_slug
from region.models import Region


@dataclass
class ElectionCategoryConfig:
    csb: RegionCategory


class ElectionCategory(Choices):
    def __new__(cls, value: str, config: ElectionCategoryConfig):
        obj = object.__new__(cls)
        obj._value_ = value
        obj._config_ = config
        return obj

    @property
    def config(self):
        return self._config_

    TK = "TK", ElectionCategoryConfig(csb=RegionCategory.STAAT), "Tweede Kamerverkiezing"
    EK = "EK", ElectionCategoryConfig(csb=RegionCategory.STAAT), "Eerste Kamerverkiezing"
    PS = "PS", ElectionCategoryConfig(csb=RegionCategory.PROVINCIE), "Provinciale Statenverkiezing"
    WS = "WS", ElectionCategoryConfig(csb=RegionCategory.WATERSCHAP), "Waterschapsverkiezing"
    GR = "GR", ElectionCategoryConfig(csb=RegionCategory.GEMEENTE), "Gemeenteraadsverkiezing"
    EP = "EP", ElectionCategoryConfig(csb=RegionCategory.STAAT), "Europees Parlementsverkiezing"


class ElectionConfigManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(date__gte=visibility_cutoff())


class ElectionConfig(BaseModel):
    objects = ElectionConfigManager()
    with_expired = models.Manager[Self]()

    identifier = models.CharField(max_length=64, unique=True)
    category = models.CharField(max_length=2, choices=ElectionCategory.choices)
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
        return ElectionCategory(self.category).config.csb

    @property
    def has_hsb(self) -> bool:
        """
        Whether this election has kieskringen with their own HSB Totaaltelling (EML_510c).

        Some election categories (e.g. waterschap) define a kieskring per CSB that is a 1:1
        structural stand-in for it, never a real subdivision with its own results -- so a
        KIESKRING region existing is not enough; only its own EML_510c data means there is
        something to show.
        """
        return Region.objects.filter(
            election__election_config=self,
            region_category=RegionCategory.KIESKRING,
            vote_counts__eml_type=EmlType.EML_510c,
        ).exists()

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
    title_nl = models.CharField(max_length=255)
    title_en = models.CharField(max_length=255, blank=True)
    date = models.DateTimeField()
    body_nl = models.TextField()
    body_en = models.TextField(blank=True)

    class Meta:
        # Entries are ordered chronologically by date.
        ordering = ("date",)

    def __str__(self):
        return f"{self.election_config.identifier} [{self.variant}]: {self.title_nl}"


class Contest(BaseModel):
    identifier = models.CharField(max_length=255, blank=True)
    election = models.ForeignKey(
        "election.Election",
        on_delete=models.CASCADE,
        related_name="contests",
    )
    name = models.CharField(max_length=255, null=True)

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

    eml_type = models.CharField(max_length=32, choices=EmlType.choices, null=True)


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


class CurrentQuerySet(models.QuerySet):
    def archive(self):
        return self.update(is_current=False)


class CurrentManager(models.Manager.from_queryset(CurrentQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_current=True)


class ElectionDocument(BaseModel):
    """
    Archivable ElectionDoc
    """

    class FileType(models.TextChoices):
        """
        Available file types, prefixed with the extensions (i.e. EML, PDF).
        Make sure to also update FILE_TYPE_MAPPINGS in the frontend code on change.
        """

        EML_510B = "EML510b", "Telling GSB"
        EML_510C = "EML510c", "Totaaltelling HSB"
        EML_510D = "EML510d", "Totaaltelling CSB"

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

    file_type = models.CharField(
        max_length=32,
        choices=FileType.choices,
        default=FileType.EML_510B,
        help_text="Type of the election document",
    )
    is_current = models.BooleanField(default=True, db_index=True)

    objects = CurrentManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        constraints = [
            models.UniqueConstraint(
                fields=["region", "file_type"],
                condition=Q(is_current=True),
                name="unique_current_document_per_region_and_file_type",
            )
        ]


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
