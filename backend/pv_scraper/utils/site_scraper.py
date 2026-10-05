"""Scrape the PVs from one authority's website: decide which links to visit and which files to keep."""

import hashlib
import heapq
import json
import logging
import random
import re
import time
from urllib.parse import unquote, urldefrag, urlsplit

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from pv_scraper.models import ScrapedFile, ScrapeSource, ScrapeStatus
from pv_scraper.utils.link_rules import (
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
)
from pv_scraper.utils.site_crawler import CrawledPage, Link, SiteCrawler

logger = logging.getLogger(__name__)

MAX_DEPTH = 2
MAX_PAGES = 80
# Links at this depth are visited for their files only: if they turn out to be pages, their links are not followed.
FILES_ONLY = MAX_DEPTH + 1


def pause(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


class SiteScraper:
    """The state of one scrape of a source: the links still to visit, and what was found, rejected or failed."""

    def __init__(self, source: ScrapeSource, crawler: SiteCrawler):
        self.source = source
        self.crawler = crawler
        self.start_urls = list(dict.fromkeys([source.website, *source.election_pages]))
        self.hosts = {host(url) for url in self.start_urls}
        self.exclude = re.compile(source.exclude) if source.exclude else None
        files = list(source.scraped_files.order_by("downloaded_at"))
        # The latest download per URL, whose etag and last-modified make the next request conditional.
        self.known_files = {file.url: file for file in files}
        self.known_hashes = {file.sha256 for file in files}

        self.queue: list[tuple[int, int, int, Link]] = []
        self.seen: set[str] = set()
        self.pages: list[dict] = []
        self.rejected: list[dict] = []
        self.errors: list[dict] = []

    def run(self) -> ScrapeStatus:
        try:
            for url in self.start_urls:
                self.push(Link(url), 0, 0)
            for site_host in sorted(self.hosts):
                if site_host.startswith("mijnstembureau-"):
                    self.mijnstembureau(f"https://{site_host}")
            self.crawl()
            status = self.status()
        except Exception as exc:
            logger.exception("Scrape of %s failed", self.source)
            self.errors.append({"url": None, "error": repr(exc)})
            status = ScrapeStatus.ERROR
        self.save_state(status)
        return status

    def status(self) -> ScrapeStatus:
        if self.known_hashes:
            return ScrapeStatus.OK
        if self.pages and all(p["status"] in (401, 403) or p.get("blocked") for p in self.pages):
            return ScrapeStatus.BLOCKED
        if not any(isinstance(p["status"], int) and p["status"] < 400 for p in self.pages):
            return ScrapeStatus.GONE
        return ScrapeStatus.NO_PVS_FOUND

    def push(self, link: Link, depth: int, priority: int) -> None:
        parts = urlsplit(link.href)
        key = f"{host(link.href)}{parts.path.rstrip('/')}?{parts.query}"
        if key not in self.seen:
            self.seen.add(key)
            heapq.heappush(self.queue, (priority, depth, len(self.seen), link))

    def crawl(self) -> None:
        visited = 0
        while self.queue and visited < MAX_PAGES:
            _, depth, _, link = heapq.heappop(self.queue)
            known = self.known_files.get(link.href)
            conditional = {}
            if known and known.etag:
                conditional["If-None-Match"] = known.etag
            if known and known.last_modified:
                conditional["If-Modified-Since"] = known.last_modified
            result = self.crawler.crawl(link.href, conditional)
            if result.file is not None:
                self.keep_file(link, result)
                continue

            visited += 1
            record = {"url": link.href, "depth": depth, "status": result.status}
            self.pages.append(record)
            if result.error:
                record["error"] = result.error
                continue
            if result.blocked:
                record["blocked"] = True
                continue
            if isinstance(result.status, int) and result.status >= 400:
                continue
            record["links"] = len(result.links)
            if depth < FILES_ONLY:
                self.handle_links(result, depth)
            pause(1, 2)

    def handle_links(self, page: CrawledPage, depth: int) -> None:
        page_host = host(page.url)
        results_page = is_results_context(f"{unquote(page.url)} {page.title}")

        for link in page.links:
            # Pleio file links open a viewer page; the file itself sits under /file/download/.
            href = PLEIO_VIEW_RE.sub(r"\1/file/download/", urldefrag(link.href)[0])
            if not href.startswith("http") or NON_PDF_RE.search(href) or NO_FOLLOW_RE.search(href):
                continue
            if self.exclude and self.exclude.search(href):
                continue
            link = Link(href, link.text, link.title, link.heading)
            doc_context = f"{unquote(href)} {link.text} {link.title} {link.heading}"
            # Election pages also link national forms and guidance; off-site files need an explicit PV name. Not in the
            # query or heading: share buttons carry the page's own URL and sit under its headings.
            if host(href) not in self.hosts | {page_host}:
                if PV_STRONG_RE.search(f"{unquote(urlsplit(href).path)} {link.text} {link.title}"):
                    self.push(link, FILES_ONLY, 0)
                continue

            follow_context = f"{unquote(href)} {link.text}"
            file_context = f"{unquote(urlsplit(href).path.rsplit('/', 1)[-1])} {link.text} {link.title}"
            may_be_pv = is_pv(doc_context, file_context)[0]
            # Below a results page, the subpages per stembureau carry only a location name.
            child_of_results = results_page and href.startswith(page.url.rstrip("/") + "/")
            if not (FOLLOW_RE.search(follow_context) or child_of_results or may_be_pv):
                continue
            # A link to the counts often leads to a subpage that lists the PDFs, however deep it sits.
            free = FREE_FOLLOW_RE.search(href) or child_of_results or is_results_context(follow_context)
            next_depth = depth if free else depth + 1
            if next_depth > MAX_DEPTH and not may_be_pv:
                continue
            # Links about the counts are visited before links about elections in general.
            self.push(link, min(next_depth, FILES_ONLY), 0 if is_results_context(doc_context) else 1)

    def mijnstembureau(self, origin: str) -> None:
        """mijnstembureau-* sites render PVs as buttons; their JSON API lists them per election."""
        url = f"{origin}/uitslagen/api/uitslagen"
        result = self.crawler.crawl(url)
        record = {"url": url, "depth": 0, "status": result.status}
        self.pages.append(record)
        try:
            elections = json.loads(result.file) if result.file and result.status < 400 else []
        except ValueError as exc:
            record["error"] = str(exc).splitlines()[0]
            return
        if result.error:
            record["error"] = result.error
        record["links"] = len(elections)
        for election in elections:
            for pv in election.get("pvKeys") or []:
                href = f"{origin}/uitslagen/api/view-pv/{election['uitslagId']}/{pv['_id']}"
                link = Link(href, pv.get("omschrijving", ""), heading=election.get("verkiezingNaam", ""))
                self.push(link, FILES_ONLY, 0)

    def keep_file(self, link: Link, result: CrawledPage) -> None:
        """Store a file that may be a PV and differs from the ones already downloaded."""
        if result.status == 304:
            return
        body, headers = result.file, result.headers
        if not body.startswith(b"%PDF"):
            self.rejected.append({"url": link.href, "text": link.text, "reason": f"not-pdf (HTTP {result.status})"})
            return
        name = filename_for(link.href, headers, link.text)
        file_context = f"{name} {link.text} {link.title}"
        pv, reason = is_pv(f"{unquote(link.href)} {file_context} {link.heading}", file_context)
        if not pv:
            self.rejected.append({"url": link.href, "text": link.text, "reason": reason})
            return

        sha256 = hashlib.sha256(body).hexdigest()
        known = self.known_files.get(link.href)
        if sha256 in self.known_hashes:
            # Unchanged content under new headers: keep them, so the next request can be answered with a 304.
            if known and known.sha256 == sha256:
                known.etag, known.last_modified = headers.get("etag"), headers.get("last-modified")
                known.save(update_fields=["etag", "last_modified", "updated_at"])
            return
        key = default_storage.save(f"pv_scraper/{self.source.code}/{name}", ContentFile(body))
        # A changed file at a known URL is a new version; the earlier one stays.
        self.known_files[link.href] = ScrapedFile.objects.create(
            source=self.source,
            url=link.href,
            sha256=sha256,
            size=len(body),
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            link_text=link.text,
            heading_text=link.heading,
        )
        self.known_hashes.add(sha256)
        logger.info("Downloaded %s from %s", key, self.source)
        pause(0.5, 1)

    def save_state(self, status: ScrapeStatus) -> None:
        """Merge this run's records into the source, keeping when each was first seen."""
        now = timezone.now()
        seen_at = now.isoformat(timespec="seconds")

        def merge(existing: list[dict], records: list[dict], *key_fields: str) -> list[dict]:
            merged = {tuple(entry.get(f) for f in key_fields): entry for entry in existing}
            for record in records:
                key = tuple(record.get(f) for f in key_fields)
                first_seen = merged[key]["first_seen"] if key in merged else seen_at
                merged[key] = record | {"first_seen": first_seen, "last_seen": seen_at}
            return list(merged.values())

        source = self.source
        source.pages = merge(source.pages, self.pages, "url")
        source.rejected = merge(source.rejected, self.rejected, "url")
        source.errors = merge(source.errors, self.errors, "url", "error")
        source.last_run_finished_at = now
        source.last_run_status = status
        source.save(
            update_fields=["pages", "rejected", "errors", "last_run_finished_at", "last_run_status", "updated_at"]
        )
