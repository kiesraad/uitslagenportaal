import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from pv_scraper.tests.factories import ScrapedFileFactory, ScrapeSourceFactory


@pytest.mark.django_db
def test_scrape_source_code_is_unique():
    ScrapeSourceFactory(code="gm0344")

    with pytest.raises(IntegrityError):
        ScrapeSourceFactory(code="gm0344")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fields",
    [{"code": "gm344"}, {"election_pages": ["not a url"]}, {"election_pages": "https://www.gm0344.nl/"}],
)
def test_scrape_source_validation_rejects(fields):
    source = ScrapeSourceFactory.build(**fields)

    with pytest.raises(ValidationError):
        source.full_clean()


@pytest.mark.django_db
def test_scraped_file_hash_is_unique_per_source():
    source = ScrapedFileFactory(sha256="a" * 64).source

    with pytest.raises(IntegrityError):
        ScrapedFileFactory(source=source, sha256="a" * 64)


@pytest.mark.django_db
def test_scraped_file_hash_may_repeat_across_sources():
    """Authorities sharing a website (Haarlem and Zandvoort) each keep their own copy of a file."""
    ScrapedFileFactory(sha256="a" * 64)

    assert ScrapedFileFactory(sha256="a" * 64).pk
