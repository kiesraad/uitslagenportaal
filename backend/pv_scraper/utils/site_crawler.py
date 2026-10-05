"""Visit pages of an authority's website in a Playwright browser and fetch files with the browser's cookies."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import requests
from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright, sync_playwright

from pv_scraper.utils.link_rules import host

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
COOKIE_LABELS = [
    "Alles accepteren",
    "Accepteer alle cookies",
    "Alle cookies accepteren",
    "Cookies toestaan",
    "Accepteren",
    "Akkoord",
    "Accepteer",
]
BLOCKED_RE = re.compile(r"captcha|just a moment|access denied|attention required|verify you are human", re.IGNORECASE)
# Errors a request for a single URL can raise.
FETCH_ERRORS = (Error, requests.RequestException)

COLLECT_JS = """
() => {
  const out = [];
  let heading = '';
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  for (let el = walker.currentNode; el; el = walker.nextNode()) {
    if (/^H[1-4]$/.test(el.tagName)) heading = el.innerText.trim().slice(0, 200);
    if (el.tagName === 'A' && el.href) {
      out.push({
        href: el.href,
        text: (el.innerText || '').trim().slice(0, 300),
        title: el.getAttribute('title') || el.getAttribute('aria-label') || '',
        heading,
      });
    }
  }
  return out;
}
"""

REVEAL_JS = """
() => {
  document.querySelectorAll('details:not([open])').forEach(d => d.open = true);
  // Header, nav and form buttons open menus or search, and some of those navigate away.
  const safe = b => !b.closest('header, nav, form, [role="search"], [role="navigation"]') && b.type !== 'submit';
  let clicked = 0;
  for (const b of document.querySelectorAll('button[aria-expanded="false"]')) {
    if (clicked++ > 150) break;
    if (safe(b)) { try { b.click(); } catch (e) {} }
  }
  for (const b of document.querySelectorAll('button, a[role="button"]')) {
    const label = (b.innerText || '').trim();
    if (safe(b) && /^(toon|laad|bekijk) (meer|alle)/i.test(label)) { try { b.click(); } catch (e) {} }
  }
  window.scrollTo(0, document.body.scrollHeight);
}
"""

logger = logging.getLogger(__name__)


@dataclass
class Link:
    href: str
    text: str = ""
    title: str = ""
    heading: str = ""


@dataclass
class CrawledPage:
    url: str
    status: int | None = None
    headers: dict = field(default_factory=dict)
    # The body of a response that is not an HTML page; None for a page.
    file: bytes | None = None
    title: str = ""
    links: list[Link] = field(default_factory=list)
    blocked: bool = False
    error: str | None = None
    # Where the page moved to, when it was reached through 301 and 308 redirects within the site only.
    permanent_redirect: str | None = None


class SiteCrawler:
    """A browser for one website; use as a context manager.

    Playwright's sync API runs an event loop on its thread, where Django refuses database queries. The browser
    therefore lives on a thread of its own, and crawl() hands its work to it.
    """

    def __init__(self, cookie_banner_label: str | None = None):
        self.cookie_labels = ([cookie_banner_label] if cookie_banner_label else []) + COOKIE_LABELS
        self.cookies_done: set[str] = set()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self):
        self._on_browser_thread(self._start)
        return self

    def __exit__(self, *exc_info):
        try:
            self._on_browser_thread(self._stop)
        finally:
            self.executor.shutdown()

    def crawl(self, url: str, headers: dict[str, str] | None = None) -> CrawledPage:
        """Request a URL; render it in the browser when it is an HTML page, or return the file otherwise."""
        return self._on_browser_thread(self._crawl, url, headers)

    def _on_browser_thread(self, fn, *args):
        return self.executor.submit(fn, *args).result()

    def _start(self) -> None:
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
        # Bot protection compares the UA with the browser's client hints, so a spoofed version gets a 403.
        user_agent = UA.replace("Chrome/130.0", f"Chrome/{self.browser.version}")
        self.context = self.browser.new_context(user_agent=user_agent, locale="nl-NL", accept_downloads=True)
        self.page = self.context.new_page()

    def _stop(self) -> None:
        try:
            if self.browser:
                self.browser.close()
        except Error:
            pass
        finally:
            if self.playwright:
                self.playwright.stop()

    def _crawl(self, url: str, headers: dict[str, str] | None) -> CrawledPage:
        try:
            status, response_headers, body = self._fetch(url, headers)
        except FETCH_ERRORS as exc:
            return CrawledPage(url, error=str(exc).splitlines()[0])
        # A 304 has no content type: it answers a conditional request for a known file.
        if status == 304 or "html" not in response_headers.get("content-type", ""):
            logger.info("Crawled %s: file download (status %d)", url, status)
            return CrawledPage(url, status, response_headers, file=body)
        if status >= 400:
            logger.info("Crawled %s: status %d", url, status)
            return CrawledPage(url, status, response_headers)

        page = self.page
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except Error as exc:
            return CrawledPage(url, error=str(exc).splitlines()[0])
        result = CrawledPage(page.url, response.status if response else None)
        if response and response.status >= 400:
            return result
        if response and response.url != url and host(response.url) == host(url):
            hops, request = [], response.request.redirected_from
            while request:
                hops.append(request.response())
                request = request.redirected_from
            if hops and all(hop and hop.status in (301, 308) for hop in hops):
                result.permanent_redirect = response.url
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Error:
            pass

        if host(page.url) not in self.cookies_done:
            self.accept_cookies()
            self.cookies_done.add(host(page.url))
        try:
            page.evaluate(REVEAL_JS)
            page.wait_for_timeout(1_500)
            links = page.evaluate(COLLECT_JS)
            result.title = page.title()
        except Error as exc:
            result.error = str(exc).splitlines()[0]
            logger.info("Crawled %s: error %s", url, result.error)
            return result
        if BLOCKED_RE.search(result.title) or (len(links) < 3 and BLOCKED_RE.search(page.content())):
            result.blocked = True
            logger.info("Crawled %s: blocked", url)
            return result
        result.url = page.url
        result.links = [Link(**link) for link in links]
        logger.info("Crawled %s: found %d links", url, len(links))
        return result

    def accept_cookies(self) -> None:
        for label in self.cookie_labels:
            try:
                button = self.page.get_by_role("button", name=label, exact=True).first
                if button.is_visible(timeout=500):
                    button.click(timeout=2_000)
                    self.page.wait_for_timeout(1_000)
                    return
            except Error:
                continue

    def _fetch(self, url: str, headers: dict[str, str] | None) -> tuple[int, dict, bytes]:
        """Fetch with the browser's cookies; fall back to requests for servers whose headers Playwright rejects."""
        try:
            response = self.context.request.get(url, headers=headers, timeout=60_000, max_redirects=10)
            return response.status, response.headers, response.body()
        except Error as exc:
            if "Parse Error" not in str(exc):
                raise
        response = requests.get(url, headers={"User-Agent": UA, **(headers or {})}, timeout=60)
        return response.status_code, {k.lower(): v for k, v in response.headers.items()}, response.content
