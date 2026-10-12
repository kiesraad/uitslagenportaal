import logging
from unittest.mock import MagicMock, call, patch

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.utils import timezone

from eml_import.utils.named_bytes_io import NamedBytesIO
from eml_import.utils.pdf_file_handler import DEFAULT_PV_DIRECTORY
from pv_scraper import tasks
from pv_scraper.models import ScrapeStatus
from pv_scraper.tasks import classify_scraped_file, dispatch_scrape_tasks, run_scrape_for_source
from pv_scraper.tests.factories import ScrapedFileFactory, ScrapeSourceFactory
from pv_scraper.utils.pv_classifier import (
    STORAGE_ENTRY,
    ClassificationResult,
    PvClassificationException,
    PvClassifier,
    ResultMatch,
)
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
@patch.object(tasks.classify_scraped_file, "apply_async")
def test_scrape_stores_each_file_and_queues_its_classification(apply_async, *_):
    source = ScrapeSourceFactory(code="gm0228")
    files = [
        FileResult(True, NamedBytesIO(b"%PDF", name), ScrapedFileFactory(source=source))
        for name in ("first.pdf", "next.pdf")
    ]

    with patch.object(SiteScraper, "crawl", return_value=iter(files)):
        run_scrape_for_source(source.id)

    assert apply_async.call_args_list == [
        call(
            (source.pk, f"classification_queue/gm0228_{file.content.name}", file.content.name),
            queue="scraper",
        )
        for file in files
    ]
    assert storages[STORAGE_ENTRY].open("classification_queue/gm0228_first.pdf").read() == b"%PDF"
    source.refresh_from_db()
    assert source.last_run_status != ScrapeStatus.ERROR


@pytest.mark.django_db
@patch("pv_scraper.utils.site_crawler.SiteCrawler.__exit__", return_value=False)
@patch("pv_scraper.utils.site_crawler.SiteCrawler.__enter__", return_value=MagicMock())
@patch.object(tasks.classify_scraped_file, "apply_async", side_effect=RuntimeError("no broker"))
def test_scrape_whose_hand_off_fails_ends_in_error(*_):
    source = ScrapeSourceFactory(code="gm0228")
    file = FileResult(True, NamedBytesIO(b"%PDF", "pv.pdf"), ScrapedFileFactory(source=source))

    with patch.object(SiteScraper, "crawl", return_value=iter([file])), pytest.raises(RuntimeError):
        run_scrape_for_source(source.id)

    source.refresh_from_db()
    assert source.last_run_status == ScrapeStatus.ERROR
    assert source.last_run_finished_at is not None


@pytest.fixture
def stored_file():
    source = ScrapeSourceFactory()
    key = storages[STORAGE_ENTRY].save("classification_queue/gm0228_pv_suffix.pdf", ContentFile(b"%PDF"))
    return source, key


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("matched_on", "saved"),
    [(ResultMatch.CODE_TITLE, True), (ResultMatch.CODE, False)],
)
def test_classify_scraped_file_stores_only_a_certain_pv(stored_file, matched_on, saved):
    source, key = stored_file
    with (
        patch.object(PvClassifier, "classify", return_value=ClassificationResult("N 10-2", matched_on)),
        patch.object(PvClassifier, "save_to_storage", autospec=True) as save_to_storage,
    ):
        classify_scraped_file(source.pk, key, "pv.pdf")

    assert save_to_storage.called == saved
    if saved:
        classifier, saved_for, folder = save_to_storage.call_args.args
        assert (classifier.file.name, classifier.file.getvalue()) == ("pv.pdf", b"%PDF")
        assert (saved_for, folder) == (source, DEFAULT_PV_DIRECTORY)
    # Classified or discarded, the file has left the classification queue.
    assert not storages[STORAGE_ENTRY].exists(key)


@pytest.mark.django_db
def test_classify_scraped_file_logs_a_pv_it_cannot_store(stored_file, caplog):
    source, key = stored_file
    with (
        caplog.at_level(logging.INFO, logger="pv_scraper.tasks"),
        patch.object(PvClassifier, "classify", return_value=ClassificationResult("N 10-2", ResultMatch.CODE_TITLE)),
        patch.object(PvClassifier, "save_to_storage", side_effect=PvClassificationException("region not known")),
    ):
        classify_scraped_file(source.pk, key, "pv.pdf")

    assert "region not known" in caplog.text
    assert storages[STORAGE_ENTRY].exists(key)
