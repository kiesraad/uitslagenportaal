from unittest.mock import call, patch

import pytest

from pv_scraper import tasks
from pv_scraper.tasks import dispatch_scrape_tasks
from pv_scraper.tests.factories import ScrapeSourceFactory


@pytest.mark.django_db
@patch.object(tasks.run_scrape_for_source, "apply_async")
def test_dispatch_sends_scrapes_to_the_scraper_queue(apply_async, settings):
    settings.PV_SCRAPER_DISPATCH_MAX_TASKS = 1
    source = ScrapeSourceFactory()

    dispatch_scrape_tasks()

    assert apply_async.call_args_list == [call((source.id,), queue="scraper")]
