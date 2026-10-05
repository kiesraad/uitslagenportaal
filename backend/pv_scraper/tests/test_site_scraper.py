from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.core.files.storage import default_storage
from django.utils import timezone

from pv_scraper.models import ScrapedFile, ScrapedPage, ScrapeStatus
from pv_scraper.tests.factories import ScrapedFileFactory, ScrapedPageFactory, ScrapeSourceFactory
from pv_scraper.utils import site_scraper
from pv_scraper.utils.site_crawler import CrawledPage, Link
from pv_scraper.utils.site_scraper import SiteScraper

PDF = b"%PDF-1.7 proces-verbaal"
WEBSITE = "https://www.gm0001.nl/"
LONG_AGO = timezone.now() - timedelta(days=40)
YEAR = timezone.localdate().year


def sha256(body: bytes) -> str:
    return site_scraper.hashlib.sha256(body).hexdigest()


def etag(body: bytes) -> str:
    return f'"{sha256(body)[:8]}"'


def page(url: str, *links: Link) -> CrawledPage:
    return CrawledPage(url, 200, links=list(links))


class FakeCrawler:
    """Answers with files and pages from dicts, with an etag per file content; anything else is a 404 page."""

    def __init__(self, pages: dict[str, CrawledPage] = None, files: dict[str, bytes] = None, headers: dict = None):
        self.pages = pages or {}
        self.files = files or {}
        # Extra response headers per file URL.
        self.headers = headers or {}
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
            headers = {"etag": etag(body), "content-type": "application/pdf", **self.headers.get(url, {})}
            return CrawledPage(url, 200, headers, file=body)
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
    ps_pdf_url = "https://www.gm0001.nl/media/centrum.pdf"
    links = [
        Link(pdf_url, "Proces-verbaal stembureau 1"),
        Link(ps_pdf_url, "Centrum", heading=f"Verkiezingen PS {YEAR}"),
    ]
    files = {pdf_url: PDF, ps_pdf_url: PDF + b" PS"}

    status = scrape(source, FakeCrawler({WEBSITE: page(WEBSITE, *links)}, files))

    scraped = ScrapedFile.objects.get(source=source, url=pdf_url)
    # The election and model are left to the OCR classification.
    assert (scraped.election, scraped.model, scraped.size, scraped.etag) == (None, None, len(PDF), etag(PDF))
    assert default_storage.exists("pv_scraper/gm0001/pv-stembureau-1.pdf")
    assert ScrapedFile.objects.filter(source=source, url=ps_pdf_url).exists()
    assert status == ScrapeStatus.OK
    source.refresh_from_db()
    assert source.last_run_status == ScrapeStatus.OK


@pytest.mark.django_db
def test_link_is_a_file_when_its_response_is_not_a_page():
    source = ScrapeSourceFactory(website=WEBSITE)
    url = "https://www.gm0001.nl/dsresource?objectid=1&type=pdf"
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, Link(url, "Stembureau 1", heading="Processen-verbaal"))}, {url: PDF})

    scrape(source, crawler)

    assert list(source.scraped_pages.values_list("url", flat=True)) == [WEBSITE]
    scraped = ScrapedFile.objects.get(source=source)
    assert (scraped.url, scraped.link_text, scraped.heading_text) == (url, "Stembureau 1", "Processen-verbaal")


@pytest.mark.django_db
def test_off_site_links_are_only_visited_for_files():
    source = ScrapeSourceFactory(website=WEBSITE)
    off_site_page = "https://www.other.nl/processen-verbaal"
    # Named after the polling station only; the heading says what it is.
    cdn_file = "https://cuatro.sim-cdn.nl/gm0001/uploads/gm0001_1_centrum_gr26.pdf?cb=x"
    heading = "De processen-verbaal van de stembureaus"
    links = [
        Link("https://www.rijksoverheid.nl/documenten/folder.pdf", "Folder verkiezingen"),
        Link(f"https://www.facebook.com/sharer.php?u={WEBSITE}processen-verbaal", "Deel", heading=heading),
        Link(cdn_file, "gm0001_1_centrum_gr26.pdf PDF, 600 kB", heading=heading),
        Link(off_site_page, "Processen-verbaal"),
    ]
    pages = {
        WEBSITE: page(WEBSITE, *links),
        off_site_page: page(off_site_page, Link("https://www.other.nl/uitslag", "Uitslag")),
    }
    crawler = FakeCrawler(pages, {cdn_file: PDF})

    scrape(source, crawler)

    assert crawler.crawled_urls == [WEBSITE, cdn_file, off_site_page]
    assert ScrapedFile.objects.get(url=cdn_file).rejected_reason is None


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
def test_rejected_files_are_recorded_but_not_stored_or_downloaded_again():
    source = ScrapeSourceFactory(code="gm0001", website=WEBSITE)
    excluded_url = "https://www.gm0001.nl/media/garantstelling.pdf"
    not_pdf_url = "https://www.gm0001.nl/media/pv-2.pdf"
    links = [Link(excluded_url, "Uitslag verkiezingen"), Link(not_pdf_url, "Proces-verbaal 2")]
    files = {excluded_url: PDF, not_pdf_url: b"<xml/>"}

    status = scrape(source, FakeCrawler({WEBSITE: page(WEBSITE, *links)}, files))

    assert sorted(ScrapedFile.objects.values_list("url", "rejected_reason")) == [
        (excluded_url, "excluded"),
        (not_pdf_url, "not-pdf (HTTP 200)"),
    ]
    assert not default_storage.exists("pv_scraper/gm0001/garantstelling.pdf")
    assert status == ScrapeStatus.NO_PVS_FOUND

    crawler = FakeCrawler({WEBSITE: page(WEBSITE, *links)}, files)
    assert scrape(source, crawler) == ScrapeStatus.NO_PVS_FOUND
    assert crawler.crawled[1:] == [
        (excluded_url, {"If-None-Match": etag(PDF)}),
        (not_pdf_url, {"If-None-Match": etag(b"<xml/>")}),
    ]
    assert ScrapedFile.objects.count() == 2


@pytest.mark.django_db
def test_follow_links_are_visited_results_first():
    source = ScrapeSourceFactory(website=WEBSITE)
    links = [
        Link("https://www.gm0001.nl/verkiezingen-tweede-kamer", "Tweede Kamer"),
        Link("https://www.gm0001.nl/uitslag-gemeenteraad", "Uitslag gemeenteraad"),
        Link(f"https://www.gm0001.nl/verkiezingen-{YEAR}", f"Verkiezingen {YEAR}"),
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
        f"https://www.gm0001.nl/verkiezingen-{YEAR}",
    ]


@pytest.mark.django_db
def test_links_about_earlier_years_only_are_skipped():
    source = ScrapeSourceFactory(website=WEBSITE)
    current = [
        # Digits in the query are no year.
        Link(f"{WEBSITE}media/pv-1.pdf?cb=2019", "Proces-verbaal 1"),
        Link(f"{WEBSITE}uitslagen", f"Uitslagen 2019 tot en met {YEAR}"),
    ]
    earlier = [
        Link(f"{WEBSITE}uploads/0717_pv_stembureau_1_veere_tk23.pdf", "0717_pv_stembureau_1_veere_tk23"),
        Link(f"{WEBSITE}verkiezingen-{YEAR - 1}", "Uitslag"),
        Link(f"{WEBSITE}media/sb-2.pdf", "Proces-verbaal stembureau 2", heading=f"Gemeenteraad {YEAR - 4}"),
    ]
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, *earlier, *current)})

    with patch.object(site_scraper.timezone, "localdate", return_value=date(YEAR, 6, 1)):
        scrape(source, crawler)

    assert crawler.crawled_urls == [WEBSITE, *(link.href for link in current)]


@pytest.mark.django_db
@pytest.mark.parametrize("month, visited", [(3, True), (4, False)])
def test_previous_year_is_followed_early_in_the_year(month, visited):
    """An election in the autumn still publishes its PVs in the new year."""
    source = ScrapeSourceFactory(website=WEBSITE)
    link = Link(f"{WEBSITE}uitslag-tk{(YEAR - 1) % 100}", "Uitslag")
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, link)})

    with patch.object(site_scraper.timezone, "localdate", return_value=date(YEAR, month, 1)):
        scrape(source, crawler)

    assert (link.href in crawler.crawled_urls) == visited


@pytest.mark.django_db
def test_file_named_after_an_earlier_year_is_rejected():
    source = ScrapeSourceFactory(website=WEBSITE)
    url = f"{WEBSITE}download/123"
    disposition = {"content-disposition": 'attachment; filename="pv_stembureau_1_gr22.pdf"'}
    crawler = FakeCrawler({WEBSITE: page(WEBSITE, Link(url, "Proces-verbaal 1"))}, {url: PDF}, {url: disposition})

    scrape(source, crawler)

    assert ScrapedFile.objects.get(url=url).rejected_reason == "outdated (2022)"


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
def test_pages_are_kept_across_runs():
    source = ScrapeSourceFactory(website=WEBSITE)
    ScrapedPageFactory(source=source, url=WEBSITE, status=500, first_seen=LONG_AGO, last_seen=LONG_AGO)
    old = ScrapedPageFactory(source=source, url=f"{WEBSITE}old", last_seen=LONG_AGO)

    scrape(source, FakeCrawler({WEBSITE: page(WEBSITE)}))

    current = ScrapedPage.objects.get(source=source, url=WEBSITE)
    assert (current.status, current.first_seen) == (200, LONG_AGO)
    assert current.last_seen > LONG_AGO
    old.refresh_from_db()
    assert old.last_seen == LONG_AGO


HUB = f"{WEBSITE}verkiezingen"
RESULTS = f"{WEBSITE}verkiezingen/uitslag"
PDF_URL = f"{WEBSITE}media/pv-1.pdf"


def site_with_hub() -> FakeCrawler:
    pages = {
        WEBSITE: page(WEBSITE, Link(HUB, "Verkiezingen")),
        HUB: page(HUB, Link(RESULTS, "Uitslag")),
        RESULTS: page(RESULTS, Link(PDF_URL, "Proces-verbaal 1")),
    }
    return FakeCrawler(pages, {PDF_URL: PDF})


@pytest.mark.django_db
def test_page_leading_to_the_files_page_becomes_an_election_page():
    source = ScrapeSourceFactory(website=WEBSITE)

    scrape(source, site_with_hub())

    source.refresh_from_db()
    assert source.election_pages == [HUB]
    results = ScrapedPage.objects.get(url=RESULTS)
    assert (results.via, results.root, results.files) == (HUB, WEBSITE, 1)

    # The next scrape starts there, without the home page; the same page with a trailing slash is no new entry.
    source.election_pages = [f"{HUB}/"]
    source.save()
    crawler = site_with_hub()
    crawler.pages[f"{HUB}/"] = crawler.pages[HUB]
    scrape(source, crawler)

    assert crawler.crawled_urls == [f"{HUB}/", RESULTS, PDF_URL]
    source.refresh_from_db()
    assert source.election_pages == [f"{HUB}/"]


@pytest.mark.django_db
def test_files_page_linked_from_the_home_page_becomes_an_election_page_itself():
    source = ScrapeSourceFactory(website=WEBSITE)
    pages = {WEBSITE: page(WEBSITE, Link(RESULTS, "Uitslag")), RESULTS: page(RESULTS, Link(PDF_URL, "Proces-verbaal"))}

    scrape(source, FakeCrawler(pages, {PDF_URL: PDF}))

    source.refresh_from_db()
    assert source.election_pages == [RESULTS]


@pytest.mark.django_db
def test_page_about_one_election_gives_way_to_the_general_election_page_above_it():
    source = ScrapeSourceFactory(website=WEBSITE)
    election = f"{HUB}/gemeenteraad-{YEAR}"
    results = f"{election}/uitslag"
    pages = {
        WEBSITE: page(WEBSITE, Link(HUB, "Verkiezingen")),
        HUB: page(HUB, Link(election, f"Gemeenteraad {YEAR}")),
        election: page(election, Link(results, "Uitslag")),
        results: page(results, Link(PDF_URL, "Proces-verbaal 1")),
    }

    scrape(source, FakeCrawler(pages, {PDF_URL: PDF}))

    source.refresh_from_db()
    assert source.election_pages == [HUB]


@pytest.mark.django_db
@pytest.mark.parametrize("answered", [True, False])
def test_folder_in_the_url_of_a_start_page_with_files_is_promoted_once_it_answered(answered):
    folder = f"{WEBSITE}bestuur/verkiezingen"
    files_page = f"{folder}/gemeenteraadsverkiezingen/uitslag"
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[files_page])
    if answered:
        ScrapedPageFactory(source=source, url=f"{folder}/", status=200)

    scrape(source, FakeCrawler({files_page: page(files_page, Link(PDF_URL, "Proces-verbaal 1"))}, {PDF_URL: PDF}))

    source.refresh_from_db()
    assert source.election_pages == ([files_page, f"{folder}/"] if answered else [files_page])


@pytest.mark.django_db
def test_short_url_is_judged_by_the_page_it_redirects_to():
    """A short URL for the latest results looks general, but lands on the results of one election."""
    short = f"{WEBSITE}verkiezingsuitslag"
    folder = f"{WEBSITE}bestuur/verkiezingen"
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[short])
    ScrapedPageFactory(source=source, url=folder, status=200)
    landed = CrawledPage(f"{folder}/tweede-kamerverkiezing/uitslag", 200, links=[Link(PDF_URL, "Proces-verbaal 1")])

    scrape(source, FakeCrawler({short: landed}, {PDF_URL: PDF}))

    source.refresh_from_db()
    assert source.election_pages == [short, folder]


@pytest.mark.django_db
def test_start_page_keeps_the_page_it_was_found_on_to_walk_up_from():
    files_page = f"{WEBSITE}uitslag-gemeenteraad"
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[files_page])
    ScrapedPageFactory(source=source, url=HUB)
    ScrapedPageFactory(source=source, url=files_page, via=HUB)

    scrape(source, FakeCrawler({files_page: page(files_page, Link(PDF_URL, "Proces-verbaal 1"))}, {PDF_URL: PDF}))

    source.refresh_from_db()
    assert source.election_pages == [files_page, HUB]
    assert ScrapedPage.objects.get(url=files_page).via == HUB


@pytest.mark.django_db
def test_walk_up_stops_at_a_page_not_about_elections():
    """The council's pages are no start for elections, so the page that led to the files is used instead."""
    source = ScrapeSourceFactory(website=WEBSITE)
    council = f"{WEBSITE}bestuur-en-gemeenteraad"
    results = f"{WEBSITE}uitslag-gemeenteraad-{YEAR}"
    pages = {
        WEBSITE: page(WEBSITE, Link(council, "Bestuur en gemeenteraad")),
        council: page(council, Link(results, f"Uitslag gemeenteraad {YEAR}")),
        results: page(results, Link(PDF_URL, "Proces-verbaal 1")),
    }

    scrape(source, FakeCrawler(pages, {PDF_URL: PDF}))

    source.refresh_from_db()
    assert source.election_pages == [council]


@pytest.mark.django_db
@pytest.mark.parametrize("days, removed", [(8, True), (1, False)])
def test_election_page_is_removed_after_a_week_of_404(days, removed):
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[HUB])
    missing_since = timezone.now() - timedelta(days=days)
    ScrapedPageFactory(source=source, url=HUB, status=404, missing_since=missing_since)

    scrape(source, FakeCrawler())

    source.refresh_from_db()
    assert source.election_pages == ([] if removed else [HUB])
    assert ScrapedPage.objects.get(url=HUB).missing_since == missing_since
    errors = [error["error"] for error in source.errors if error["url"] == HUB]
    assert errors == ([f"Removed from election_pages: 404 or 410 since {missing_since:%Y-%m-%d}"] if removed else [])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "result", [CrawledPage(HUB, 403), CrawledPage(HUB, 503), CrawledPage(HUB, error="net::ERR_TIMED_OUT")]
)
def test_blocked_or_failing_election_page_is_not_missing(result):
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[HUB])

    scrape(source, FakeCrawler({HUB: result}))

    source.refresh_from_db()
    assert source.election_pages == [HUB]
    assert ScrapedPage.objects.get(url=HUB).missing_since is None


@pytest.mark.django_db
@pytest.mark.parametrize("days, max_pages, removed", [(31, 80, True), (29, 80, False), (31, 1, False)])
def test_election_page_is_removed_after_a_month_without_files(days, max_pages, removed):
    """A crawl cut short by MAX_PAGES may not have reached the files, so it doesn't count."""
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[HUB])
    ScrapedPageFactory(source=source, url=HUB, first_seen=timezone.now() - timedelta(days=days))

    with patch.object(site_scraper, "MAX_PAGES", max_pages):
        scrape(source, FakeCrawler({HUB: page(HUB, Link(RESULTS, "Uitslag"))}))

    source.refresh_from_db()
    assert source.election_pages == ([] if removed else [HUB])


@pytest.mark.django_db
def test_election_page_with_files_is_kept_however_old():
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[HUB])
    ScrapedPageFactory(source=source, url=HUB, first_seen=LONG_AGO)

    scrape(source, site_with_hub())

    source.refresh_from_db()
    assert source.election_pages == [HUB]
    assert ScrapedPage.objects.get(url=HUB).last_file_at > LONG_AGO


@pytest.mark.django_db
def test_election_page_that_moved_permanently_is_replaced():
    source = ScrapeSourceFactory(website=WEBSITE, election_pages=[HUB])
    moved = f"{WEBSITE}stemmen"

    scrape(source, FakeCrawler({HUB: CrawledPage(moved, 200, permanent_redirect=moved)}))

    source.refresh_from_db()
    assert source.election_pages == [moved]
    assert source.errors[0]["error"] == f"Replaced in election_pages by {moved} (permanent redirect)"
