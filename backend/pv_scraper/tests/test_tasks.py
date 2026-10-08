from unittest.mock import MagicMock, call, patch

import pytest
from django.utils import timezone

from eml_import.utils.named_bytes_io import NamedBytesIO
from pv_scraper import tasks
from pv_scraper.models import ScrapeStatus
from pv_scraper.tasks import dispatch_scrape_tasks, run_scrape_for_source
from pv_scraper.tests.factories import ScrapedFileFactory, ScrapeSourceFactory
from pv_scraper.utils.pv_classifier import PvClassifier
from pv_scraper.utils.site_scraper import FileResult, SiteScraper


@pytest.mark.django_db
@patch.object(tasks.run_scrape_for_source, "apply_async")
def test_dispatch_sends_scrapes_to_the_scraper_queue(apply_async, settings):
    settings.PV_SCRAPER_DISPATCH_MAX_TASKS = 1
    source = ScrapeSourceFactory()

    dispatch_scrape_tasks()

    assert apply_async.call_args_list == [call((source.id,), queue="scraper")]


@pytest.mark.django_db
@patch.object(tasks.run_scrape_for_source, "apply_async")
def test_dispatch_marks_sources_as_queued_once(apply_async, settings):
    settings.PV_SCRAPER_DISPATCH_MAX_TASKS = 5
    source = ScrapeSourceFactory()

    dispatch_scrape_tasks()
    dispatch_scrape_tasks()

    source.refresh_from_db()
    assert (source.last_run_status, source.last_run_started_at is not None) == (ScrapeStatus.QUEUED, True)
    assert apply_async.call_count == 1

    source.scrape_requested_at = timezone.now()
    source.save()
    dispatch_scrape_tasks()

    assert apply_async.call_count == 2


@pytest.mark.django_db
@patch.object(tasks.run_scrape_for_source, "apply_async")
def test_dispatch_skips_disabled_sources(apply_async, settings):
    settings.PV_SCRAPER_DISPATCH_MAX_TASKS = 5
    source = ScrapeSourceFactory(disabled=True)

    dispatch_scrape_tasks()

    source.refresh_from_db()
    assert source.scrape_requested_at is None
    apply_async.assert_not_called()


@pytest.mark.django_db
@patch("pv_scraper.utils.site_crawler.SiteCrawler.__enter__", side_effect=RuntimeError("no browser"))
def test_scrape_that_fails_to_start_ends_in_error(_):
    source = ScrapeSourceFactory()

    with pytest.raises(RuntimeError):
        run_scrape_for_source(source.id)

    source.refresh_from_db()
    assert source.last_run_status == ScrapeStatus.ERROR
    assert source.last_run_finished_at is not None


@pytest.mark.django_db
@patch("pv_scraper.utils.site_crawler.SiteCrawler.__exit__")
@patch("pv_scraper.utils.site_crawler.SiteCrawler.__enter__", return_value=MagicMock())
def test_file_that_fails_to_classify_does_not_end_the_scrape(*_):
    source = ScrapeSourceFactory()
    files = [
        FileResult(True, NamedBytesIO(b"%PDF", name), ScrapedFileFactory(source=source))
        for name in ("broken.pdf", "next.pdf")
    ]

    with (
        patch.object(SiteScraper, "crawl", return_value=iter(files)),
        patch.object(PvClassifier, "classify", side_effect=[RuntimeError("bad pdf"), None]) as classify,
    ):
        run_scrape_for_source(source.id)

    source.refresh_from_db()
    assert classify.call_count == 2
    assert source.last_run_status != ScrapeStatus.ERROR
    assert source.last_run_finished_at is not None
