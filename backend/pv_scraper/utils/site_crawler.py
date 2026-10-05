"""Visit pages of an authority's website in a Playwright browser and fetch files with the browser's cookies."""

import re
from dataclasses import dataclass, field

import requests
from playwright.sync_api import Browser, BrowserContext, Error, Page

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
# Errors fetch() can raise for a single URL.
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


@dataclass
class Link:
    href: str
    text: str = ""
    title: str = ""
    heading: str = ""


@dataclass
class CrawledPage:
    url: str
    # HTTP status, or "download" when the URL turned out to be a file.
    status: int | str | None = None
    title: str = ""
    links: list[Link] = field(default_factory=list)
    blocked: bool = False
    error: str | None = None


class SiteCrawler:
    """One browser context for one website; use as a context manager."""

    def __init__(self, browser: Browser, cookie_banner_label: str | None = None):
        self.browser = browser
        self.cookie_labels = ([cookie_banner_label] if cookie_banner_label else []) + COOKIE_LABELS
        self.cookies_done: set[str] = set()
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self):
        # Bot protection compares the UA with the browser's client hints, so a spoofed version gets a 403.
        user_agent = UA.replace("Chrome/130.0", f"Chrome/{self.browser.version}")
        self.context = self.browser.new_context(user_agent=user_agent, locale="nl-NL", accept_downloads=True)
        self.page = self.context.new_page()
        return self

    def __exit__(self, *exc_info):
        try:
            self.context.close()
        except Error:
            pass

    def crawl(self, url: str) -> CrawledPage:
        page = self.page
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except Error as exc:
            if "Download is starting" in str(exc):
                return CrawledPage(url, "download")
            return CrawledPage(url, error=str(exc).splitlines()[0])
        result = CrawledPage(page.url, response.status if response else None)
        if response and response.status >= 400:
            return result
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
            return result
        if BLOCKED_RE.search(result.title) or (len(links) < 3 and BLOCKED_RE.search(page.content())):
            result.blocked = True
            return result
        result.url = page.url
        result.links = [Link(**link) for link in links]
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

    def fetch(self, url: str, headers: dict[str, str] | None = None) -> tuple[int, dict, bytes]:
        """Fetch with the browser's cookies; fall back to requests for servers whose headers Playwright rejects."""
        try:
            response = self.context.request.get(url, headers=headers, timeout=60_000, max_redirects=10)
            return response.status, response.headers, response.body()
        except Error as exc:
            if "Parse Error" not in str(exc):
                raise
        response = requests.get(url, headers={"User-Agent": UA, **(headers or {})}, timeout=60)
        return response.status_code, {k.lower(): v for k, v in response.headers.items()}, response.content
