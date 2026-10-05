from unittest.mock import patch

import pytest
from django.core.files.storage import default_storage

from pv_scraper.models import ScrapedFile, ScrapeStatus
from pv_scraper.tests.factories import ScrapedFileFactory, ScrapeSourceFactory
from pv_scraper.utils import site_scraper
from pv_scraper.utils.site_crawler import CrawledPage, Link
from pv_scraper.utils.site_scraper import SiteScraper

PDF = b"%PDF-1.7 proces-verbaal"
WEBSITE = "https://www.gm0001.nl/"


def sha256(body: bytes) -> str:
    return site_scraper.hashlib.sha256(body).hexdigest()


def etag(body: bytes) -> str:
    return f'"{sha256(body)[:8]}"'


def page(url: str, *links: Link) -> CrawledPage:
    return CrawledPage(url, 200, links=list(links))


class FakeCrawler:
    """Answers with files and pages from dicts, with an etag per file content; anything else is a 404 page."""

    def __init__(self, pages: dict[str, CrawledPage] = None, files: dict[str, bytes] = None):
        self.pages = pages or {}
        self.files = files or {}
        self.crawled: list[tuple[str, dict]] = []

    @property
    def crawled_urls(self) -> list[str]:
        return [url for url, _ in self.crawled]

    def crawl(self, url: str, headers: dict | None = None) -> CrawledPage:
        self.crawled.append((url, headers or {}))
        if url in self.files:
            body = self.files[url]
            if (headers or {}).get("If-None-Match") == etag(body):
                return CrawledPage(url, 304, {"etag": etag(body)}, file=b"")
            return CrawledPage(url, 200, {"etag": etag(body), "content-type": "application/pdf"}, file=body)
        return self.pages.get(url, CrawledPage(url, 404))


@pytest.fixture(autouse=True)
def no_pauses():
    with patch.object(site_scraper, "pause"):
        yield


def scrape(source, crawler) -> ScrapeStatus:
    return SiteScraper(source, crawler).run()


@pytest.mark.django_db
def test_pv_links_of_any_election_are_downloaded_to_storage():
    source = ScrapeSourceFactory(code="gm0001", website=WEBSITE)
    pdf_url = "https://www.gm0001.nl/media/pv-stembureau-1.pdf"
    old_pdf_url = "https://www.gm0001.nl/media/centrum.pdf"
    links = [Link(pdf_url, "Proces-verbaal stembureau 1"), Link(old_pdf_url, "Centrum", heading="Verkiezingen PS 2019")]
    files = {pdf_url: PDF, old_pdf_url: PDF + b" 2019"}

    status = scrape(source, FakeCrawler({WEBSITE: page(WEBSITE, *links)}, files))

    scraped = ScrapedFile.objects.get(source=source, url=pdf_url)
    # The election and model are left to the OCR classification.
    assert (scraped.election, scraped.model, scraped.size, scraped.etag) == (None, None, len(PDF), etag(PDF))
    assert default_storage.exists("pv_scraper/gm0001/pv-stembureau-1.pdf")
    assert ScrapedFile.objects.filter(source=source, url=old_pdf_url).exists()
    assert status == ScrapeStatus.OK
    source.refresh_from_db()
    assert source.last_run_status == ScrapeStatus.OK


@pytest.mark.django_db
def test_link_is_a_file_when_its_response_is_not_a_page():
    source = ScrapeSourceFactory(website=WEBSITE)
    url = "https://www.gm0001.nl/dsresource?objectid=1&type=pdf"
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, Link(url, "Stembureau 1", heading="Processen-verbaal"))}, {url: PDF})

    scrape(source, crawler)

    source.refresh_from_db()
    assert [p["url"] for p in source.pages] == [WEBSITE]
    scraped = ScrapedFile.objects.get(source=source)
    assert (scraped.url, scraped.link_text, scraped.heading_text) == (url, "Stembureau 1", "Processen-verbaal")


@pytest.mark.django_db
def test_off_site_links_are_only_visited_for_files():
    source = ScrapeSourceFactory(website=WEBSITE)
    off_site_page = "https://www.other.nl/processen-verbaal"
    links = [
        Link("https://www.rijksoverheid.nl/documenten/folder.pdf", "Folder verkiezingen"),
        Link(f"https://www.facebook.com/sharer.php?u={WEBSITE}processen-verbaal", "Deel", heading="Processen-verbaal"),
        Link(off_site_page, "Processen-verbaal"),
    ]
    pages = {
        WEBSITE: page(WEBSITE, *links),
        off_site_page: page(off_site_page, Link("https://www.other.nl/uitslag", "Uitslag")),
    }
    crawler = FakeCrawler(pages)

    scrape(source, crawler)

    assert crawler.crawled_urls == [WEBSITE, off_site_page]


@pytest.mark.django_db
def test_unchanged_file_is_not_stored_again():
    source = ScrapeSourceFactory(website=WEBSITE)
    known_url = "https://www.gm0001.nl/media/pv-1.pdf"
    moved_url = "https://www.gm0001.nl/media/pv-1-copy.pdf"
    ScrapedFileFactory(source=source, url=known_url, sha256=sha256(PDF), etag=etag(PDF), last_modified="Mon, 1 Jun")
    links = [Link(known_url, "Proces-verbaal 1"), Link(moved_url, "Proces-verbaal 1")]
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, *links)}, {known_url: PDF, moved_url: PDF})

    scrape(source, crawler)

    assert crawler.crawled == [
        (WEBSITE, {}),
        (known_url, {"If-None-Match": etag(PDF), "If-Modified-Since": "Mon, 1 Jun"}),
        (moved_url, {}),
    ]
    assert ScrapedFile.objects.filter(source=source).count() == 1


@pytest.mark.django_db
def test_changed_file_at_known_url_is_stored_as_new_version():
    source = ScrapeSourceFactory(website=WEBSITE)
    url = "https://www.gm0001.nl/media/pv-1.pdf"
    ScrapedFileFactory(source=source, url=url, sha256=sha256(PDF), etag=etag(PDF))
    corrected = PDF + b" gecorrigeerd"
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, Link(url, "Proces-verbaal 1"))}, {url: corrected})

    scrape(source, crawler)

    assert sorted(ScrapedFile.objects.filter(url=url).values_list("sha256", "etag")) == sorted(
        [(sha256(PDF), etag(PDF)), (sha256(corrected), etag(corrected))]
    )


@pytest.mark.django_db
def test_same_content_under_new_etag_updates_the_known_file():
    source = ScrapeSourceFactory(website=WEBSITE)
    url = "https://www.gm0001.nl/media/pv-1.pdf"
    known = ScrapedFileFactory(source=source, url=url, sha256=sha256(PDF), etag='"old"')
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, Link(url, "Proces-verbaal 1"))}, {url: PDF})

    scrape(source, crawler)

    known.refresh_from_db()
    assert known.etag == etag(PDF)
    assert ScrapedFile.objects.filter(source=source).count() == 1


@pytest.mark.django_db
def test_rejected_files_are_recorded():
    source = ScrapeSourceFactory(website=WEBSITE)
    excluded_url = "https://www.gm0001.nl/media/garantstelling.pdf"
    not_pdf_url = "https://www.gm0001.nl/media/pv-2.pdf"
    links = [Link(excluded_url, "Uitslag verkiezingen"), Link(not_pdf_url, "Proces-verbaal 2")]
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, *links)}, {excluded_url: PDF, not_pdf_url: b"<xml/>"})

    status = scrape(source, crawler)

    source.refresh_from_db()
    assert [(r["url"], r["reason"]) for r in source.rejected] == [
        (excluded_url, "excluded"),
        (not_pdf_url, "not-pdf (HTTP 200)"),
    ]
    assert status == ScrapeStatus.NO_PVS_FOUND


@pytest.mark.django_db
def test_follow_links_are_visited_results_first():
    source = ScrapeSourceFactory(website=WEBSITE)
    links = [
        Link("https://www.gm0001.nl/verkiezingen-tweede-kamer", "Tweede Kamer"),
        Link("https://www.gm0001.nl/uitslag-gemeenteraad", "Uitslag gemeenteraad"),
        Link("https://www.gm0001.nl/verkiezingen-2019", "Verkiezingen 2019"),
        Link("https://www.gm0001.nl/afval", "Afval"),
        Link("https://www.gm0001.nl/zoeken?q=verkiezingen", "Zoeken"),
        Link("https://www.other.nl/verkiezingen", "Elders"),
    ]
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, *links)})

    scrape(source, crawler)

    assert crawler.crawled_urls == [
        WEBSITE,
        "https://www.gm0001.nl/uitslag-gemeenteraad",
        "https://www.gm0001.nl/verkiezingen-tweede-kamer",
        "https://www.gm0001.nl/verkiezingen-2019",
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "result, expected",
    [
        (CrawledPage(WEBSITE, 403), ScrapeStatus.BLOCKED),
        (CrawledPage(WEBSITE, 200, blocked=True), ScrapeStatus.BLOCKED),
        (CrawledPage(WEBSITE, 404), ScrapeStatus.GONE),
        (CrawledPage(WEBSITE, error="net::ERR_NAME_NOT_RESOLVED"), ScrapeStatus.GONE),
        (CrawledPage(WEBSITE, 200), ScrapeStatus.NO_PVS_FOUND),
    ],
)
def test_status_without_files(result, expected):
    source = ScrapeSourceFactory(website=WEBSITE)

    assert scrape(source, FakeCrawler({WEBSITE: result})) == expected


@pytest.mark.django_db
def test_unexpected_error_is_recorded():
    source = ScrapeSourceFactory(website=WEBSITE)
    crawler = FakeCrawler()
    crawler.crawl = lambda url, headers=None: 1 / 0

    assert scrape(source, crawler) == ScrapeStatus.ERROR
    source.refresh_from_db()
    assert source.errors[0]["error"] == "ZeroDivisionError('division by zero')"


@pytest.mark.django_db
def test_state_is_merged_with_earlier_runs():
    source = ScrapeSourceFactory(
        website=WEBSITE,
        pages=[
            {"url": WEBSITE, "status": 500, "first_seen": "2026-01-01T00:00:00+00:00", "last_seen": "x"},
            {"url": "https://www.gm0001.nl/old", "status": 200, "first_seen": "x", "last_seen": "x"},
        ],
    )

    scrape(source, FakeCrawler({WEBSITE: page(WEBSITE)}))

    source.refresh_from_db()
    current, old = sorted(source.pages, key=lambda p: p["url"])
    assert (current["status"], current["first_seen"]) == (200, "2026-01-01T00:00:00+00:00")
    assert current["last_seen"] != "x"
    assert old["last_seen"] == "x"
