"""Scrape the PVs from one authority's website: decide which links to visit and which files to keep."""

import hashlib
import heapq
import json
import logging
import random
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generator
from urllib.parse import unquote, urldefrag, urlsplit

from django.utils import timezone

from eml_import.utils.named_bytes_io import NamedBytesIO
from pv_scraper.models import ScrapedFile, ScrapedPage, ScrapeSource, ScrapeStatus
from pv_scraper.utils.link_rules import (
    ELECTION_PAGE_RE,
    FILE_PATH_RE,
    FOLLOW_RE,
    FREE_FOLLOW_RE,
    NO_FOLLOW_RE,
    NON_PDF_RE,
    PLEIO_VIEW_RE,
    PV_STRONG_RE,
    filename_for,
    host,
    is_pv,
    is_results_context,
    newest_year,
)
from pv_scraper.utils.site_crawler import CrawledPage, Link, SiteCrawler

logger = logging.getLogger(__name__)

MAX_DEPTH = 2
MAX_PAGES = 80
# Links at this depth are visited for their files only: if they turn out to be pages, their links are not followed.
FILES_ONLY = MAX_DEPTH + 1
# An election page is dropped after answering 404 or 410 this long, or leading to no PV files this long.
GONE_AFTER = timedelta(days=7)
NO_FILES_AFTER = timedelta(days=30)
# Links and files about years before the current one are skipped, except the previous year during these months.
GRACE_MONTHS = 3


def pause(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


def url_key(url: str) -> str:
    """The same page, with or without "www." or a trailing slash."""
    parts = urlsplit(urldefrag(url)[0])
    return f"{host(url)}{parts.path.rstrip('/')}?{parts.query}"


@dataclass
class Visit:
    link: Link
    depth: int
    # The page whose link is followed (None for a start point), and the start point it descends from.
    via: str | None
    root: str


@dataclass
class FileResult:
    is_pv: bool
    content: NamedBytesIO | None = None
    scraped_file: ScrapedFile | None = None


class SiteScraper:
    """The state of one scrape of a source: the links still to visit, and what was found, rejected or failed."""

    def __init__(self, source: ScrapeSource, crawler: SiteCrawler):
        self.source = source
        self.crawler = crawler
        # Start from the election pages; without any, crawl the whole website to find them.
        self.start_urls = list(dict.fromkeys(source.election_pages or [source.website]))
        self.hosts = {host(source.website)} | {host(url) for url in self.start_urls}
        self.exclude = re.compile(source.exclude) if source.exclude else None
        today = timezone.localdate()
        # Early in the year, PVs of an election late in the previous year are still being published.
        self.oldest_year = today.year - (1 if today.month <= GRACE_MONTHS else 0)
        files: list[ScrapedFile] = list(source.scraped_files.order_by("downloaded_at"))
        # The latest download per URL, whose etag and last-modified make the next request conditional.
        self.known_files = {file.url: file for file in files}
        self.known_hashes = {file.sha256 for file in files}
        self.pv_hashes = {file.sha256 for file in files if not file.rejected_reason}

        self.queue: list[tuple[int, int, int, Visit]] = []
        self.seen: set[str] = set()
        # Whether every link worth visiting was visited, rather than the crawl stopping at MAX_PAGES.
        self.complete = False
        self.pages: list[dict] = []
        self.titles: dict[str, str] = {}
        # Where a page ended up after redirects, when that differs from its link.
        self.final_urls: dict[str, str] = {}
        self.files_by_page: Counter[str] = Counter()
        self.files_by_root: Counter[str] = Counter()
        self.redirects: dict[str, str] = {}
        self.errors: list[dict] = []

    def run(self) -> Generator[FileResult, None, ScrapeStatus]:
        try:
            for url in self.start_urls:
                self.push(Visit(Link(url), 0, None, url), 0)
            for url in self.start_urls:
                if host(url).startswith("mijnstembureau-"):
                    self.mijnstembureau(f"https://{urlsplit(url).netloc}", url)
            yield from self.crawl()
            status = self.status()
        except Exception as exc:
            logger.exception("Scrape of %s failed", self.source)
            self.errors.append({"url": None, "error": repr(exc)})
            status = ScrapeStatus.ERROR
        self.save_state(status)
        return status

    def status(self) -> ScrapeStatus:
        if self.pv_hashes:
            return ScrapeStatus.OK
        if self.pages and all(p["status"] in (401, 403) or p["blocked"] for p in self.pages):
            return ScrapeStatus.BLOCKED
        if not any(p["status"] is not None and p["status"] < 400 for p in self.pages):
            return ScrapeStatus.GONE
        return ScrapeStatus.NO_PVS_FOUND

    def push(self, visit: Visit, priority: int) -> None:
        key = url_key(visit.link.href)
        if key not in self.seen:
            self.seen.add(key)
            heapq.heappush(self.queue, (priority, visit.depth, len(self.seen), visit))

    def crawl(self) -> Generator[FileResult]:
        visited = 0
        while self.queue and visited < MAX_PAGES:
            _, _, _, visit = heapq.heappop(self.queue)
            url = visit.link.href
            known = self.known_files.get(url)
            conditional = {}
            if known and known.etag:
                conditional["If-None-Match"] = known.etag
            if known and known.last_modified:
                conditional["If-Modified-Since"] = known.last_modified
            result = self.crawler.crawl(url, conditional)
            if result.file is not None:
                file_result = self.keep_file(visit.link, result)
                if file_result.is_pv:
                    self.files_by_page[visit.via] += 1
                    self.files_by_root[visit.root] += 1

                if file_result.content:
                    yield file_result

                continue

            visited += 1
            record = self.record_page(visit, result)
            if result.permanent_redirect and visit.via is None:
                self.redirects[url] = result.permanent_redirect
            if result.error or result.blocked or (result.status is not None and result.status >= 400):
                continue
            record["links"] = len(result.links)
            self.titles[url] = result.title
            if result.url != url:
                self.final_urls[url] = result.url
            if visit.depth < FILES_ONLY:
                self.handle_links(visit, result)
            pause(1, 2)
        self.complete = not self.queue

    def outdated(self, text: str) -> bool:
        """Whether a text is about an earlier year only: archives keep the PVs of elections long past."""
        year = newest_year(text)
        return year is not None and year < self.oldest_year

    def record_page(self, visit: Visit, result: CrawledPage) -> dict:
        record = {
            "url": visit.link.href,
            "via": visit.via,
            "root": visit.root,
            "depth": visit.depth,
            "status": result.status,
            "error": result.error,
            "blocked": result.blocked,
            "links": None,
        }
        self.pages.append(record)
        return record

    def handle_links(self, visit: Visit, page: CrawledPage) -> None:
        page_host = host(page.url)
        results_page = is_results_context(f"{unquote(page.url)} {page.title}")

        for link in page.links:
            # Pleio file links open a viewer page; the file itself sits under /file/download/.
            href = PLEIO_VIEW_RE.sub(r"\1/file/download/", urldefrag(link.href)[0])
            if not href.startswith("http") or NON_PDF_RE.search(href) or NO_FOLLOW_RE.search(href):
                continue
            if self.exclude and self.exclude.search(href):
                continue
            # Not the query, whose ids and cache keys can hold digits that look like a year.
            if self.outdated(f"{unquote(urlsplit(href).path)} {link.text} {link.title} {link.heading}"):
                continue
            link = Link(href, link.text, link.title, link.heading)
            path = unquote(urlsplit(href).path)
            doc_context = f"{unquote(href)} {link.text} {link.title} {link.heading}"
            file_context = f"{path.rsplit('/', 1)[-1]} {link.text} {link.title}"
            may_be_pv = is_pv(doc_context, file_context)[0]
            # Election pages also link national forms and guidance, so off-site links need an explicit PV name. Share
            # buttons carry the page's own URL in their query and sit under its headings, so a heading only counts for
            # a link to a file, such as the PDFs that sites built on one platform keep on a shared CDN.
            if host(href) not in self.hosts | {page_host}:
                if PV_STRONG_RE.search(f"{path} {link.text} {link.title}") or (FILE_PATH_RE.search(path) and may_be_pv):
                    self.push(Visit(link, FILES_ONLY, visit.link.href, visit.root), 0)
                continue

            follow_context = f"{unquote(href)} {link.text}"
            # Below a results page, the subpages per stembureau carry only a location name.
            child_of_results = results_page and href.startswith(page.url.rstrip("/") + "/")
            if not (FOLLOW_RE.search(follow_context) or child_of_results or may_be_pv):
                continue
            # A link to the counts often leads to a subpage that lists the PDFs, however deep it sits.
            free = FREE_FOLLOW_RE.search(href) or child_of_results or is_results_context(follow_context)
            next_depth = visit.depth if free else visit.depth + 1
            if next_depth > MAX_DEPTH and not may_be_pv:
                continue
            # Links about the counts are visited before links about elections in general.
            child = Visit(link, min(next_depth, FILES_ONLY), visit.link.href, visit.root)
            self.push(child, 0 if is_results_context(doc_context) else 1)

    def mijnstembureau(self, origin: str, root: str) -> None:
        """mijnstembureau-* sites render PVs as buttons; their JSON API lists them per election."""
        url = f"{origin}/uitslagen/api/uitslagen"
        result = self.crawler.crawl(url)
        record = self.record_page(Visit(Link(url), 0, None, root), result)
        try:
            elections = json.loads(result.file) if result.file and result.status < 400 else []
        except ValueError as exc:
            record["error"] = str(exc).splitlines()[0]
            return
        record["links"] = len(elections)
        for election in elections:
            if self.outdated(election.get("verkiezingNaam", "")):
                continue
            for pv in election.get("pvKeys") or []:
                href = f"{origin}/uitslagen/api/view-pv/{election['uitslagId']}/{pv['_id']}"
                link = Link(href, pv.get("omschrijving", ""), heading=election.get("verkiezingNaam", ""))
                # Credited to the start page rather than the API, which is no page to start from.
                self.push(Visit(link, FILES_ONLY, root, root), 0)

    def keep_file(self, link: Link, result: CrawledPage) -> FileResult:
        """Record a downloaded file and store it when it may be a PV; return whether it is one."""
        assert result.file is not None, "Call keep_file() only if result has a file"

        known: ScrapedFile | None = self.known_files.get(link.href)
        if result.status == 304:
            return FileResult(bool(known) and not known.rejected_reason, scraped_file=known)
        body, headers = result.file, result.headers
        file_name = filename_for(link.href, headers, link.text)
        if not body.startswith(b"%PDF"):
            rejected_reason = f"not-pdf (HTTP {result.status})"
        else:
            file_context = f"{file_name} {link.text} {link.title}"
            rejected_reason = is_pv(f"{unquote(link.href)} {file_context} {link.heading}", file_context)[1] or None
        # The name the server gives a file can show its year where the link did not.
        if not rejected_reason and self.outdated(file_name):
            rejected_reason = f"outdated ({newest_year(file_name)})"

        sha256 = hashlib.sha256(body).hexdigest()
        if sha256 in self.known_hashes:
            # Unchanged content under new headers: keep them, so the next request can be answered with a 304.
            if known and known.sha256 == sha256:
                known.etag, known.last_modified = headers.get("etag"), headers.get("last-modified")
                known.save(update_fields=["etag", "last_modified", "updated_at"])
            return FileResult(sha256 in self.pv_hashes, scraped_file=known)

        # A changed file at a known URL is a new version; the earlier one stays.
        scraped_file = ScrapedFile.objects.create(
            source=self.source,
            url=link.href,
            sha256=sha256,
            size=len(body),
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            link_text=link.text,
            heading_text=link.heading,
            rejected_reason=rejected_reason,
        )
        self.known_files[link.href] = scraped_file
        self.known_hashes.add(sha256)

        # Yield only non-rejected files
        # Rejected files are recorded to prevent re-downloads but not returned for processing
        if not rejected_reason:
            logger.info("Downloaded file from %s", self.source)
            self.pv_hashes.add(sha256)
            return FileResult(True, NamedBytesIO(body, file_name), scraped_file)

        return FileResult(not rejected_reason, scraped_file=scraped_file)

    def hubs(self) -> list[str]:
        """The pages to start the next scrape from, one for each page with PV files."""
        website = url_key(self.source.website)
        # How pages were reached and whether they answered, over all runs with this one taking precedence: a start page
        # has no "via" of its own this run, but the run that found it recorded one.
        parents, answered = {}, {}
        stored = self.source.scraped_pages.values_list("url", "via", "status", "blocked")
        for url, via, status, blocked in [
            *stored,
            *((r["url"], r["via"], r["status"], r["blocked"]) for r in self.pages),
        ]:
            parents[url] = via or parents.get(url)
            if status is not None and status < 400 and not blocked:
                answered[url_key(url)] = url

        hubs = []
        for record in self.pages:
            if not self.files_by_page[record["url"]]:
                continue
            hub = self.general_election_page(record["url"], parents, answered, website)
            if not hub:
                # The page that led to the files, or the files page itself when that was the home page: promoting the
                # home page would make every scrape a full crawl.
                via = record["via"]
                hub = via if via and url_key(via) != website else record["url"]
                # A page about one election never links to the next one: no start page is better than that.
                if self.is_election_page(hub) is False:
                    continue
            if url_key(hub) != website:
                hubs.append(hub)
        return hubs

    def page_path(self, url: str) -> str:
        # A short URL such as "/verkiezingsuitslag" redirects to the results of one election; judge where it lands.
        return urlsplit(self.final_urls.get(url, url)).path

    def is_election_page(self, url: str) -> bool | None:
        """True for a general election page, False for one about a single election, None if not about elections."""
        context = f"{unquote(self.page_path(url))} {self.titles.get(url, '')}"
        return None if not ELECTION_PAGE_RE.search(context) else newest_year(context) is None

    def general_election_page(
        self, url: str, parents: dict[str, str | None], answered: dict[str, str], website: str
    ) -> str | None:
        """The highest page above a page with PV files that is about elections but not about one in particular.

        Two routes lead up: the pages that linked to it, and the folders in its URL, which only count when they
        answered as a page. Pages for a single election are passed over; a route stops at the home page or at a page
        not about elections. The candidate with the fewest folders wins.
        """
        best_linked, current, visited = None, url, set()
        while current and url_key(current) != website and current not in visited:
            visited.add(current)
            general = self.is_election_page(current)
            if general is None:
                break
            if general:
                best_linked = current
            current = parents.get(current)

        best_folder = None
        parts = urlsplit(self.final_urls.get(url, url))
        folders = parts.path.strip("/").split("/")
        for count in range(len(folders) - 1, 0, -1):
            folder = f"{parts.scheme}://{parts.netloc}/{'/'.join(folders[:count])}"
            general = self.is_election_page(folder)
            if general is None:
                break
            if general and url_key(folder) in answered:
                best_folder = answered[url_key(folder)]

        candidates = [page for page in (best_linked, best_folder) if page]
        return min(candidates, key=lambda page: self.page_path(page).strip("/").count("/"), default=None)

    def save_state(self, status: ScrapeStatus) -> None:
        now = timezone.now()
        hubs = self.hubs()
        self.save_pages(now, leads_to_files={*self.files_by_page, *self.files_by_root, *hubs})
        if status != ScrapeStatus.ERROR:
            self.update_election_pages(now, hubs)

        source = self.source
        seen_at = now.isoformat(timespec="seconds")
        errors = {(entry.get("url"), entry.get("error")): entry for entry in source.errors}
        for record in self.errors:
            key = (record["url"], record["error"])
            first_seen = errors[key]["first_seen"] if key in errors else seen_at
            errors[key] = record | {"first_seen": first_seen, "last_seen": seen_at}
        source.errors = list(errors.values())
        source.last_run_finished_at = now
        source.last_run_status = status
        source.save(update_fields=["election_pages", "errors", "last_run_finished_at", "last_run_status", "updated_at"])

    def save_pages(self, now: datetime, leads_to_files: set[str]) -> None:
        existing = {page.url: page for page in self.source.scraped_pages.filter(url__in=[r["url"] for r in self.pages])}
        for record in self.pages:
            page = existing.get(record["url"]) or ScrapedPage(source=self.source, url=record["url"], first_seen=now)
            # A start page keeps the "via" of the run that found it, to walk up from later.
            via = record["via"] or page.via
            for field, value in record.items():
                setattr(page, field, value)
            page.via = via
            page.files = self.files_by_page[page.url]
            page.last_seen = now
            # Only a definite "gone" counts as missing; errors, bot walls and 5xx say nothing about the page.
            if page.status in (404, 410):
                page.missing_since = page.missing_since or now
            elif page.status is not None and page.status < 400 and not page.blocked:
                page.missing_since = None
            if page.url in leads_to_files:
                page.last_file_at = now
            page.save()

    def update_election_pages(self, now: datetime, hubs: list[str]) -> None:
        """Add the hubs that led to PV files, and drop the election pages that are gone or lead nowhere."""
        entries = list(self.source.election_pages)
        keys = {url_key(entry) for entry in entries}
        for hub in hubs:
            if url_key(hub) not in keys:
                keys.add(url_key(hub))
                entries.append(hub)
                logger.info("Added %s to the election pages of %s", hub, self.source)

        visited = {record["url"] for record in self.pages}
        pages = {page.url: page for page in self.source.scraped_pages.filter(url__in=entries)}
        kept = []
        for entry in entries:
            page = pages.get(entry)
            note = None
            files_since = page and (page.last_file_at or page.first_seen)
            if page and page.missing_since and now - page.missing_since > GONE_AFTER:
                note = f"Removed from election_pages: 404 or 410 since {page.missing_since:%Y-%m-%d}"
            elif target := self.redirects.get(entry):
                note = f"Replaced in election_pages by {target} (permanent redirect)"
                if url_key(target) not in keys:
                    keys.add(url_key(target))
                    kept.append(target)
            elif (
                page
                and self.complete
                and entry in visited
                and page.status is not None
                and page.status < 400
                and not page.blocked
                and now - files_since > NO_FILES_AFTER
            ):
                note = f"Removed from election_pages: no PV files since {files_since:%Y-%m-%d}"
            if note:
                logger.info("%s: %s", entry, note)
                self.errors.append({"url": entry, "error": note})
            else:
                kept.append(entry)
        self.source.election_pages = kept
