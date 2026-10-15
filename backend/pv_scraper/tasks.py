import hashlib
import logging
from contextlib import closing
from datetime import timedelta

from botocore.exceptions import ConnectionError as S3ConnectionError
from celery import Celery
from celery.exceptions import BackendError
from celery.schedules import crontab
from django.conf import settings
from django.core.files.storage import storages
from django.db import DatabaseError
from django.db.models import F, Q
from django.utils import timezone

from election.models import ElectionConfig
from eml_import.utils.named_bytes_io import NamedBytesIO
from eml_import.utils.pdf_file_handler import DEFAULT_PV_DIRECTORY
from mainsite.celery import app
from pv_scraper.models import ScrapedFile, ScrapeSource, ScrapeStatus
from pv_scraper.utils.pv_classifier import STORAGE_ENTRY, PvClassificationException, PvClassifier

logger = logging.getLogger(__name__)

SCRAPE_OFTEN_DAYS_AFTER_ELECTION = 14
"""
The number of days after an election to increase the scrape frequency to once each SCRAPE_INTERVAL_DURING_ELECTION
"""

SCRAPE_INTERVAL_OUTSIDE_ELECTION = timedelta(hours=24 * 7)
"""
Interval after which a source is due to be queued for scraping, in the period outside of an election.
"""

SCRAPE_INTERVAL_DURING_ELECTION = timedelta(hours=24)
"""
Interval after which a source is due to be queued for scraping,
in the `SCRAPE_OFTEN_DAYS_AFTER_ELECTION` days after an election.
"""

SCRAPER_QUEUE = "scraper"
"""
Consumed only by the worker with Playwright and Tesseract (`-Q scraper` in prod.dockerfile).
"""

# Redis priorities on the scraper queue (0 is highest), so queued classifications start before queued scrapes.
CLASSIFICATION_PRIORITY = 0
SCRAPE_PRIORITY = 9

CLASSIFICATION_QUEUE_FOLDER = "classification_queue"
""" Folder on storage to store temp files waiting for classification """


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **_) -> None:
    sender.add_periodic_task(
        crontab(minute="*/10"),
        dispatch_scrape_tasks.s(),
        name="Dispatch a task which dispatches scrape tasks if needed.",
    )


@app.task
def dispatch_scrape_tasks():
    """Determine which sources to scrape and start a task for each."""
    is_recent_election = ElectionConfig.objects.filter(
        date__gte=timezone.now() - timedelta(days=SCRAPE_OFTEN_DAYS_AFTER_ELECTION), date__lte=timezone.now()
    ).exists()

    # Request a scrape for the sources that haven't been scraped in SCRAPE_INTERVAL (or never)
    # A scrape can also be requested from other parts of the application, e.g. the EML importer.
    enabled = ScrapeSource.objects.filter(disabled=False)
    interval = SCRAPE_INTERVAL_DURING_ELECTION if is_recent_election else SCRAPE_INTERVAL_OUTSIDE_ELECTION
    enabled.filter(Q(last_run_started_at__lt=timezone.now() - interval) | Q(last_run_started_at__isnull=True)).update(
        scrape_requested_at=timezone.now()
    )

    # Get the source we want to scrape, this includes the ones for which we just requested a scrape
    task_limit = settings.PV_SCRAPER_DISPATCH_MAX_TASKS
    source_ids = list(
        enabled.filter(
            Q(scrape_requested_at__gt=F("last_run_started_at"))
            | (Q(scrape_requested_at__isnull=False) & Q(last_run_started_at__isnull=True))
        )
        .order_by("last_run_finished_at")
        .values_list("id", flat=True)[:task_limit]
    )

    # Counted as started once queued, so the next dispatch does not queue the source again while it waits.
    ScrapeSource.objects.filter(pk__in=source_ids).update(
        last_run_started_at=timezone.now(), last_run_status=ScrapeStatus.QUEUED
    )
    for source_id in source_ids:
        run_scrape_for_source.apply_async((source_id,), queue=SCRAPER_QUEUE, priority=SCRAPE_PRIORITY)


@app.task(
    autoretry_for=[DatabaseError, S3ConnectionError, BackendError],
    retry_backoff=5,
    max_retries=2,
)
def run_scrape_for_source(source_id: int):
    # Only the scraper worker image has Playwright, and every worker imports this module.
    from pv_scraper.utils.site_crawler import SiteCrawler
    from pv_scraper.utils.site_scraper import SiteScraper

    storage = storages[STORAGE_ENTRY]

    source = ScrapeSource.objects.get(pk=source_id)
    source.last_run_started_at = timezone.now()
    source.last_run_status = ScrapeStatus.RUNNING
    source.save(update_fields=["last_run_started_at", "last_run_status", "updated_at"])

    try:
        # Closing the scrape saves its state before the failure of a hand-off is handled below.
        with SiteCrawler(source.cookie_banner_label) as crawler, closing(SiteScraper(source, crawler).run()) as files:
            for file in files:
                # Named after the content, as one source may publish several files under one name.
                name = f"{source.code}_{file.scraped_file.sha256}.pdf"
                key = storage.save(f"{CLASSIFICATION_QUEUE_FOLDER}/{name}", file.content)
                classify_scraped_file.apply_async(
                    (source.pk, key, file.content.name), queue=SCRAPER_QUEUE, priority=CLASSIFICATION_PRIORITY
                )
    except Exception:
        # A failure outside the scrape itself, such as the browser not starting, still ends the run.
        if source.last_run_status == ScrapeStatus.RUNNING:
            source.last_run_status = ScrapeStatus.ERROR
            source.last_run_finished_at = timezone.now()
            source.save(update_fields=["last_run_status", "last_run_finished_at", "updated_at"])
        raise


@app.task(
    autoretry_for=[DatabaseError, S3ConnectionError],
    retry_backoff=5,
    max_retries=2,
)
def classify_scraped_file(source_id: int, key: str, file_name: str) -> None:
    """
    Classify a scraped file stored under a key and store it for the PV import when its model is certain.

    The file name is the one it was published under; the classifier reads the election and stembureau from it. The
    file leaves the classification queue whatever the outcome, unless the task is retried.
    """
    storage = storages[STORAGE_ENTRY]
    source = ScrapeSource.objects.get(pk=source_id)
    with storage.open(key) as stored:
        content = NamedBytesIO(stored.read(), file_name)

    logger.info(f"Classifying {key}...")
    classifier = PvClassifier(content)
    rejected_reason = None
    try:
        classification = classifier.classify()
        if classification and classification.matched_on.is_certain():
            logger.info(f"Classified as {classification.model} for {classification.region}, saving file")
            classifier.save_to_storage(source, DEFAULT_PV_DIRECTORY)
        else:
            logger.info("Classification not certain, discarding file")
    except PvClassificationException as e:
        logger.warning(str(e))
        rejected_reason = str(e)
    except DatabaseError, S3ConnectionError:
        raise
    except Exception as ex:
        logger.exception("Classification of %s failed", key)
        rejected_reason = f"Classification failed: {ex}"

    # A PV that cannot be stored or read is recorded as rejected, with the reason cut to what the field holds.
    if rejected_reason:
        max_length = ScrapedFile._meta.get_field("rejected_reason").max_length
        ScrapedFile.objects.filter(source=source, sha256=hashlib.sha256(content.getvalue()).hexdigest()).update(
            rejected_reason=rejected_reason[:max_length]
        )
    storage.delete(key)
