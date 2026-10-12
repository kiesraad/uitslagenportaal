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

from eml_import.utils.named_bytes_io import NamedBytesIO
from eml_import.utils.pdf_file_handler import DEFAULT_PV_DIRECTORY
from mainsite.celery import app
from pv_scraper.models import ScrapeSource, ScrapeStatus
from pv_scraper.utils.pv_classifier import STORAGE_ENTRY, PvClassificationException, PvClassifier

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL = timedelta(hours=24)
"""
Interval after which a source is due to be queued for scraping
"""

SCRAPER_QUEUE = "scraper"
"""
Consumed only by the worker with Playwright and Tesseract (`-Q scraper` in prod.dockerfile).
"""

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

    # Request a scrape for the sources that haven't been scraped in SCRAPE_INTERVAL (or never)
    # A scrape can also be requested from other parts of the application, e.g. the EML importer.
    enabled = ScrapeSource.objects.filter(disabled=False)
    enabled.filter(
        Q(last_run_started_at__lt=timezone.now() - SCRAPE_INTERVAL) | Q(last_run_started_at__isnull=True)
    ).update(scrape_requested_at=timezone.now())

    # Get the source we want to scrape, this includes the ones for which we just requested a scrape
    task_limit = settings.PV_SCRAPER_DISPATCH_MAX_TASKS
    source_ids = list(
        enabled.filter(
            Q(scrape_requested_at__gt=F("last_run_started_at"))
            | (Q(scrape_requested_at__isnull=False) & Q(last_run_started_at__isnull=True))
        )
        .order_by("scrape_requested_at")
        .values_list("id", flat=True)[:task_limit]
    )

    # Counted as started once queued, so the next dispatch does not queue the source again while it waits.
    ScrapeSource.objects.filter(pk__in=source_ids).update(
        last_run_started_at=timezone.now(), last_run_status=ScrapeStatus.QUEUED
    )
    for source_id in source_ids:
        run_scrape_for_source.apply_async((source_id,), queue=SCRAPER_QUEUE)


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
                key = storage.save(f"{CLASSIFICATION_QUEUE_FOLDER}/{source.code}_{file.content.name}", file.content)
                classify_scraped_file.apply_async((source.pk, key, file.content.name), queue=SCRAPER_QUEUE)
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

    The file name is the one it was published under, which storage may have suffixed in the key; the classifier reads
    the election and stembureau from it.
    """
    storage = storages[STORAGE_ENTRY]
    source = ScrapeSource.objects.get(pk=source_id)
    with storage.open(key) as stored:
        content = NamedBytesIO(stored.read(), file_name)

    logger.info(f"Classifying {key}...")
    classifier = PvClassifier(content)
    classification = classifier.classify()
    if not classification or not classification.matched_on.is_certain():
        logger.info("Classification not certain, discarding file")
        storage.delete(key)
        return

    logger.info(f"Classified as {classification.model} for {classification.region}, saving file")
    try:
        classifier.save_to_storage(source, DEFAULT_PV_DIRECTORY)
        storage.delete(key)
    except PvClassificationException as e:
        logger.info(str(e))
