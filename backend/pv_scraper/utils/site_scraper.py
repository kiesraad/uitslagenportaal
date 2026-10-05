"""Scrape the PVs from one authority's website: decide which pages to visit and which documents to download."""

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
    DOC_URL_RE,
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
from pv_scraper.utils.site_crawler import FETCH_ERRORS, CrawledPage, Link, SiteCrawler

logger = logging.getLogger(__name__)

MAX_DEPTH = 2
MAX_PAGES = 80


def pause(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


class SiteScraper:
    """The state of one scrape of a source: the pages still to visit, and what was found, rejected or failed."""

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
        self.fetched_urls: set[str] = set()

        self.queue: list[tuple[int, int, int, str]] = []
        self.seen: set[str] = set()
        self.pages: list[dict] = []
        self.rejected: list[dict] = []
        self.errors: list[dict] = []

    def run(self) -> ScrapeStatus:
        try:
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

    def push(self, url: str, depth: int, priority: int) -> None:
        url = urldefrag(url)[0]
        parts = urlsplit(url)
        key = f"{host(url)}{parts.path.rstrip('/')}?{parts.query}"
        if key not in self.seen:
            self.seen.add(key)
            heapq.heappush(self.queue, (priority, depth, len(self.seen), url))

    def crawl(self) -> None:
        for url in self.start_urls:
            self.push(url, 0, 0)
        visited = 0
        while self.queue and visited < MAX_PAGES:
            _, depth, _, url = heapq.heappop(self.queue)
            visited += 1
            page = self.crawler.crawl(url)
            record = {"url": url, "depth": depth, "status": page.status}
            self.pages.append(record)
            if page.status == "download":
                self.download(Link(url))
                continue
            if page.error:
                record["error"] = page.error
                continue
            if page.blocked:
                record["blocked"] = True
                continue
            if isinstance(page.status, int) and page.status >= 400:
                continue
            record["links"] = len(page.links)
            self.handle_links(page, depth)
            pause(1, 2)

    def handle_links(self, page: CrawledPage, depth: int) -> None:
        page_host = host(page.url)
        page_context = f"{unquote(page.url)} {page.title}"
        results_page = is_results_context(page_context)

        for link in page.links:
            href = urldefrag(link.href)[0]
            if not href.startswith("http") or NON_PDF_RE.search(href):
                continue
            if self.exclude and self.exclude.search(href):
                continue
            if DOC_URL_RE.search(href) or re.search(r"\bpdf\b", link.text, re.IGNORECASE):
                doc_context = f"{unquote(href)} {link.text} {link.title} {link.heading}"
                # Election pages also link national forms and guidance; off-site files need an explicit PV name.
                if host(href) not in self.hosts | {page_host} and not PV_STRONG_RE.search(doc_context):
                    self.rejected.append({"url": href, "text": link.text, "reason": "off-site"})
                    continue
                self.consider_document(link, href, doc_context)
                continue
            if host(href) not in self.hosts | {page_host} or NO_FOLLOW_RE.search(href):
                continue
            follow_context = f"{unquote(href)} {link.text}"
            # Below a results page, the subpages per stembureau carry only a location name.
            child_of_results = results_page and href.startswith(page.url.rstrip("/") + "/")
            if not (FOLLOW_RE.search(follow_context) or child_of_results):
                continue
            # A link to the counts often leads to a subpage that lists the PDFs, however deep it sits.
            free = FREE_FOLLOW_RE.search(href) or child_of_results or is_results_context(follow_context)
            next_depth = depth if free else depth + 1
            if next_depth > MAX_DEPTH:
                continue
            # Pages about the counts are visited before pages about elections in general.
            self.push(href, next_depth, 0 if is_results_context(follow_context) else 1)

    def mijnstembureau(self, origin: str) -> None:
        """mijnstembureau-* sites render PVs as buttons; their JSON API lists them per election."""
        url = f"{origin}/uitslagen/api/uitslagen"
        try:
            status, _, body = self.crawler.fetch(url)
            elections = json.loads(body) if status < 400 else []
        except (*FETCH_ERRORS, ValueError) as exc:
            self.errors.append({"url": url, "error": str(exc).splitlines()[0]})
            return
        self.pages.append({"url": url, "depth": 0, "status": status, "links": len(elections)})
        for election in elections:
            name = election.get("verkiezingNaam", "")
            for pv in election.get("pvKeys") or []:
                description = pv.get("omschrijving", "")
                if not is_pv(f"{description} {name}", description)[0]:
                    self.rejected.append({"url": pv["_id"], "text": description, "reason": "excluded"})
                    continue
                href = f"{origin}/uitslagen/api/view-pv/{election['uitslagId']}/{pv['_id']}"
                self.download(Link(href, description, heading=name))

    def consider_document(self, link: Link, href: str, doc_context: str) -> None:
        file_context = f"{unquote(urlsplit(href).path.rsplit('/', 1)[-1])} {link.text} {link.title}"
        pv, reason = is_pv(doc_context, file_context)
        if not pv:
            self.rejected.append({"url": href, "text": link.text, "reason": reason})
            return
        self.download(Link(href, link.text, link.title, link.heading))

    def download(self, link: Link) -> None:
        # Pleio file links open a viewer page; the file itself sits under /file/download/.
        url = PLEIO_VIEW_RE.sub(r"\1/file/download/", link.href)
        if url in self.fetched_urls:
            return
        self.fetched_urls.add(url)
        known = self.known_files.get(url)
        conditional = {}
        if known and known.etag:
            conditional["If-None-Match"] = known.etag
        if known and known.last_modified:
            conditional["If-Modified-Since"] = known.last_modified
        for attempt in range(3):
            try:
                status, headers, body = self.crawler.fetch(url, conditional)
                break
            except FETCH_ERRORS as exc:
                if attempt == 2:
                    self.errors.append({"url": url, "error": str(exc).splitlines()[0]})
                    return
                time.sleep(2 * (attempt + 1))
        if status == 304:
            return
        if not body.startswith(b"%PDF"):
            self.rejected.append({"url": url, "text": link.text, "reason": f"not-pdf (HTTP {status})"})
            return

        sha256 = hashlib.sha256(body).hexdigest()
        if sha256 in self.known_hashes:
            # Unchanged content under new headers: keep them, so the next request can be answered with a 304.
            if known and known.sha256 == sha256:
                known.etag, known.last_modified = headers.get("etag"), headers.get("last-modified")
                known.save(update_fields=["etag", "last_modified", "updated_at"])
            return
        name = filename_for(url, headers, link.text)
        key = default_storage.save(f"pv_scraper/{self.source.code}/{name}", ContentFile(body))
        # A changed file at a known URL is a new version; the earlier one stays.
        self.known_files[url] = ScrapedFile.objects.create(
            source=self.source,
            url=url,
            sha256=sha256,
            size=len(body),
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            link_text=link.text,
            heading_text=link.heading,
        )
        self.known_hashes.add(sha256)
        logger.info("%s: %s", self.source, key)
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
