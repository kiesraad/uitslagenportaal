import json
from io import StringIO

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
    ScrapeSourceFactory(code="ws0539", name="Dommel", last_run_status=ScrapeStatus.OK, errors=[{"url": "x"}])
    save_authorities({"ws0539": {**DOMMEL, "disabled": True}})

    call_command("import_scrape_sources")

    source = ScrapeSource.objects.get(code="ws0539")
    assert (source.name, source.disabled) == ("De Dommel", True)
    assert (source.last_run_status, source.errors) == (ScrapeStatus.OK, [{"url": "x"}])


@pytest.mark.django_db
def test_import_merges_election_pages_with_those_the_scraper_found():
    found = "https://www.dommel.nl/verkiezingen/uitslagen"
    ScrapeSourceFactory(code="ws0539", election_pages=[found, "https://www.dommel.nl/verkiezingen"])
    save_authorities({"ws0539": {**DOMMEL, "election_pages": ["https://www.dommel.nl/verkiezingen", "https://a.nl/"]}})

    call_command("import_scrape_sources")

    assert ScrapeSource.objects.get(code="ws0539").election_pages == [
        found,
        "https://www.dommel.nl/verkiezingen",
        "https://a.nl/",
    ]


@pytest.mark.django_db
def test_import_skips_an_invalid_record_and_imports_the_rest():
    save_authorities({"ws0539": DOMMEL, "ws0155": {**DOMMEL, "website": "not a url"}})
    stderr = StringIO()

    call_command("import_scrape_sources", stderr=stderr)

    assert list(ScrapeSource.objects.values_list("code", flat=True)) == ["ws0539"]
    assert "Skipped ws0155: website:" in stderr.getvalue()


@pytest.mark.django_db
def test_import_leaves_an_existing_source_alone_when_its_record_is_invalid():
    ScrapeSourceFactory(code="ws0539", name="Dommel")
    save_authorities({"ws0539": {**DOMMEL, "kind": "MOERAS"}})

    call_command("import_scrape_sources", stderr=StringIO())

    assert ScrapeSource.objects.get(code="ws0539").name == "Dommel"


@pytest.mark.django_db
def test_import_ignores_unknown_fields():
    save_authorities({"ws0539": {**DOMMEL, "note": "nieuw"}})

    call_command("import_scrape_sources")

    assert ScrapeSource.objects.filter(code="ws0539").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "code, fields",
    [
        ("ws0539", {**DOMMEL, "kind": "MOERAS"}),
        ("dommel", DOMMEL),
        ("ws0539", {**DOMMEL, "election_pages": ["dommel.nl/verkiezingen"]}),
        ("ws0539", {**DOMMEL, "election_pages": "https://www.dommel.nl/verkiezingen"}),
        ("ws0539", {key: value for key, value in DOMMEL.items() if key != "name"}),
        ("ws0539", "https://www.dommel.nl/"),
    ],
)
def test_import_rejects_invalid_records(code, fields):
    save_authorities({code: fields})
    stderr = StringIO()

    call_command("import_scrape_sources", stderr=stderr)

    assert not ScrapeSource.objects.exists()
    assert f"Skipped {code}" in stderr.getvalue()


@pytest.mark.django_db
def test_import_fails_without_the_file():
    with pytest.raises(CommandError):
        call_command("import_scrape_sources")
