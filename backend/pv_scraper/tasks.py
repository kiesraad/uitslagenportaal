import logging
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone

from mainsite.celery import app
from pv_scraper.models import ScrapeSource, ScrapeStatus
from pv_scraper.utils.pv_classifier import PvClassifier

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL = timedelta(hours=24)
# Consumed only by the worker with Playwright (`-Q scraper` in prod.dockerfile).
SCRAPER_QUEUE = "scraper"


@app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **_) -> None:
    # Run the `import_next_eml_commits` task every 10 min
    sender.add_periodic_task(
        crontab(minute="*/10"),
        dispatch_scrape_tasks.s(),
        name="Dispatch a task for each source to scrape",
    )


@app.task
def dispatch_scrape_tasks():
    """Determine which sources to scrape and start a task for each."""

    # Request a scrape for the sources that haven't been scraped in SCRAPE_INTERVAL (or never)
    # A scrape can also be requested from other parts of the application, e.g. the EML importer.
    ScrapeSource.objects.filter(
        Q(last_run_started_at__lt=timezone.now() - SCRAPE_INTERVAL) | Q(last_run_started_at__isnull=True)
    ).update(scrape_requested_at=timezone.now())

    # Get the source we want to scrape, this includes the ones for which we just requested a scrape
    task_limit = settings.PV_SCRAPER_DISPATCH_MAX_TASKS
    sources = ScrapeSource.objects.filter(
        Q(scrape_requested_at__gt=F("last_run_started_at"))
        | (Q(scrape_requested_at__isnull=False) & Q(last_run_started_at__isnull=True))
    ).order_by("scrape_requested_at")[:task_limit]

    for source in sources:
        run_scrape_for_source.apply_async((source.id,), queue=SCRAPER_QUEUE)


@app.task
def run_scrape_for_source(source_id: int):
    # Only the scraper worker image has Playwright, and every worker imports this module.
    from pv_scraper.utils.site_crawler import SiteCrawler
    from pv_scraper.utils.site_scraper import SiteScraper

    source = ScrapeSource.objects.get(pk=source_id)
    source.last_run_started_at = timezone.now()
    source.last_run_status = ScrapeStatus.RUNNING
    source.save(update_fields=["last_run_started_at", "last_run_status", "updated_at"])

    with SiteCrawler(source.cookie_banner_label) as crawler:
        for file in SiteScraper(source, crawler).run():
            classifier = PvClassifier(file.content)
            classification = classifier.classify()
            if classification and classification.matched_on.is_certain():
                classifier.save_to_storage(file.scraped_file.source)
