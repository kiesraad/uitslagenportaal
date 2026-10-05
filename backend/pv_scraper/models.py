from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.db import models
from django.utils import timezone

from mainsite.models import BaseModel, RegionCategory


def validate_url_list(value) -> None:
    if not isinstance(value, list) or not all(isinstance(url, str) for url in value):
        raise ValidationError("Enter a list of URLs.")
    for url in value:
        URLValidator()(url)


class ScrapeStatus(models.TextChoices):
    RUNNING = "running", "Running"
    OK = "ok", "OK"
    NO_PVS_FOUND = "no-pvs-found", "No PVs found"
    GONE = "gone", "Gone"  # no start URL answered below 400
    BLOCKED = "blocked", "Blocked"  # every page gave 401/403 or a bot wall
    ERROR = "error", "Error"


class ScrapeSource(BaseModel):
    """The website of a gemeente, waterschap, province or the state that publishes PVs: settings and scrape state."""

    # TOOi code from the government organisation register: gm0344, ws0539, pv26; `nl` for the state.
    code = models.CharField(max_length=6, unique=True, validators=[RegexValidator(r"^(gm\d{4}|ws\d{4}|pv\d{2}|nl)$")])
    kind = models.CharField(max_length=32, choices=RegionCategory.choices)
    name = models.CharField(max_length=255)
    website = models.URLField()
    election_pages = models.JSONField(default=list, blank=True, validators=[validate_url_list])
    exclude = models.CharField(max_length=255, null=True, blank=True)
    cookie_banner_label = models.CharField(max_length=255, null=True, blank=True)
    disabled = models.BooleanField(default=False)

    # A scrape is due when it was requested after the last run started.
    scrape_requested_at = models.DateTimeField(null=True, blank=True)
    last_run_started_at = models.DateTimeField(null=True, blank=True)
    last_run_finished_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=16, choices=ScrapeStatus.choices, null=True, blank=True)

    # Merged across runs: one entry per URL (per URL and error for `errors`), each with first_seen and last_seen.
    pages = models.JSONField(default=list, blank=True)
    rejected = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ScrapedFile(BaseModel):
    """A downloaded document; the file itself goes to storage for the processing service."""

    source = models.ForeignKey(ScrapeSource, on_delete=models.CASCADE, related_name="scraped_files")
    election = models.CharField(max_length=64, null=True, blank=True)
    model = models.CharField(max_length=32, null=True, blank=True)
    url = models.TextField()
    sha256 = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    # Response headers, sent back as If-None-Match and If-Modified-Since; kept as received.
    etag = models.CharField(max_length=255, null=True, blank=True)
    last_modified = models.CharField(max_length=64, null=True, blank=True)
    link_text = models.TextField(blank=True)
    heading_text = models.TextField(blank=True)
    downloaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "sha256"], name="unique_sha256_per_source"),
        ]
        indexes = [models.Index(fields=["source", "url"], name="scrapedfile_source_url")]

    def __str__(self) -> str:
        return self.url
