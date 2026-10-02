import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError

from mainsite.models import RegionCategory
from pv_scraper.models import ScrapeSource, ScrapeStatus
from pv_scraper.tests.factories import ScrapeSourceFactory

PATH = "pv_scraper/authorities.json"
DOMMEL = {
    "kind": "WATERSCHAP",
    "name": "De Dommel",
    "website": "https://www.dommel.nl/",
    "website_source": "overheid.nl",
    "election_pages": ["https://www.dommel.nl/verkiezingen"],
    "exclude": None,
    "cookie_banner_label": "Alles accepteren",
    "disabled": False,
}


def save_authorities(authorities: dict) -> None:
    default_storage.save(PATH, ContentFile(json.dumps(authorities).encode()))


@pytest.mark.django_db
def test_import_creates_sources_from_the_file():
    save_authorities({"ws0539": DOMMEL})

    call_command("import_scrape_sources")

    source = ScrapeSource.objects.get(code="ws0539")
    assert source.kind == RegionCategory.WATERSCHAP
    assert source.name == "De Dommel"
    assert source.election_pages == ["https://www.dommel.nl/verkiezingen"]
    assert source.cookie_banner_label == "Alles accepteren"


@pytest.mark.django_db
def test_import_updates_settings_but_keeps_scrape_state():
    ScrapeSourceFactory(code="ws0539", name="Dommel", last_run_status=ScrapeStatus.OK, pages=[{"url": "x"}])
    save_authorities({"ws0539": {**DOMMEL, "disabled": True}})

    call_command("import_scrape_sources")

    source = ScrapeSource.objects.get(code="ws0539")
    assert (source.name, source.disabled) == ("De Dommel", True)
    assert (source.last_run_status, source.pages) == (ScrapeStatus.OK, [{"url": "x"}])


@pytest.mark.django_db
def test_import_fails_without_the_file():
    with pytest.raises(CommandError):
        call_command("import_scrape_sources")
