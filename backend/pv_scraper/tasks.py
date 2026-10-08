import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from mainsite.celery import app
from pv_scraper.models import ScrapeSource, ScrapeStatus
from pv_scraper.utils.pv_classifier import PvClassificationException, PvClassifier

if TYPE_CHECKING:
    from pv_scraper.utils.site_scraper import FileResult

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL = timedelta(hours=24)
# Consumed only by the worker with Playwright (`-Q scraper` in prod.dockerfile).
SCRAPER_QUEUE = "scraper"


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


def classify_and_store(file: "FileResult") -> None:
    """Classify a scraped file and store it under pvs/ when its model is certain."""
    logger.info(f"Classifying {file.content.name}...")
    classifier = PvClassifier(file.content)
    classification = classifier.classify()
    if not classification or not classification.matched_on.is_certain():
        logger.info("Classification not certain, discarding file")
        return

    logger.info(f"Classified as {classification.model} for {classification.region}, saving file")
    try:
        classifier.save_to_storage(file.scraped_file.source, "pvs")
    except PvClassificationException as e:
        logger.info(str(e))


@app.task
def run_scrape_for_source(source_id: int):
    # Only the scraper worker image has Playwright, and every worker imports this module.
    from pv_scraper.utils.site_crawler import SiteCrawler
    from pv_scraper.utils.site_scraper import SiteScraper

    source = ScrapeSource.objects.get(pk=source_id)
    source.last_run_started_at = timezone.now()
    source.last_run_status = ScrapeStatus.RUNNING
    source.save(update_fields=["last_run_started_at", "last_run_status", "updated_at"])

    try:
        with SiteCrawler(source.cookie_banner_label) as crawler:
            for file in SiteScraper(source, crawler).run():
                if file.scraped_file is None:
                    continue
                # One bad file must not end the scrape: the rest of the queue and the scrape state still count.
                try:
                    classify_and_store(file)
                except Exception:
                    logger.exception("Classifying %s failed", file.content.name)
    except Exception:
        # A failure outside the scrape itself, such as the browser not starting, still ends the run.
        if source.last_run_status == ScrapeStatus.RUNNING:
            source.last_run_status = ScrapeStatus.ERROR
            source.last_run_finished_at = timezone.now()
            source.save(update_fields=["last_run_status", "last_run_finished_at", "updated_at"])
        raise
