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
    # Where scrapes start; the scraper adds the pages that lead to PVs and drops those that no longer do. Empty means a
    # full crawl from `website`.
    election_pages = models.JSONField(default=list, blank=True, validators=[validate_url_list])
    exclude = models.CharField(max_length=255, null=True, blank=True)
    cookie_banner_label = models.CharField(max_length=255, null=True, blank=True)
    disabled = models.BooleanField(default=False)

    # A scrape is due when it was requested after the last run started.
    scrape_requested_at = models.DateTimeField(null=True, blank=True)
    last_run_started_at = models.DateTimeField(null=True, blank=True)
    last_run_finished_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=16, choices=ScrapeStatus.choices, null=True, blank=True)

    # Merged across runs: one entry per URL and error, with first_seen and last_seen. Also notes changes to
    # election_pages.
    errors = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ScrapedPage(BaseModel):
    """A page visited while scraping a source, kept across runs to choose and prune the election pages."""

    source = models.ForeignKey(ScrapeSource, on_delete=models.CASCADE, related_name="scraped_pages")
    url = models.TextField()
    # The page whose link led here, and the election page (or website) the visit started from.
    via = models.TextField(null=True, blank=True)
    root = models.TextField()
    depth = models.PositiveSmallIntegerField()
    status = models.PositiveSmallIntegerField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    blocked = models.BooleanField(default=False)
    links = models.PositiveIntegerField(null=True, blank=True)
    # PV files linked from this page on its last visit.
    files = models.PositiveIntegerField(default=0)
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)
    # Start of an unbroken run of 404 and 410 answers.
    missing_since = models.DateTimeField(null=True, blank=True)
    # When a PV file was last reached from this page, directly or through the pages below it.
    last_file_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "url"], name="unique_page_url_per_source")]

    def __str__(self) -> str:
        return self.url


class ScrapedFile(BaseModel):
    """A downloaded document. Unless rejected, the file itself goes to storage for the processing service."""

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
    # Why the file is not a PV, such as "excluded" or "not-pdf (HTTP 200)"; kept so it is not downloaded again.
    rejected_reason = models.CharField(max_length=64, null=True, blank=True)
    downloaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "sha256"], name="unique_sha256_per_source"),
        ]
        indexes = [models.Index(fields=["source", "url"], name="scrapedfile_source_url")]

    def __str__(self) -> str:
        return self.url
