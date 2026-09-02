"""
The furniture the result pages share: search, source documents, the timeline and the
page index. Asserted once here rather than on every route that renders them.
"""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright

BORSELE = "/ab2023/gsb/654-borsele/csb/17-scheldestromen"
BORSELE_RESULTS = f"{BORSELE}/resultaten"


def test_searching_the_gemeente_list_navigates_to_the_gemeente(page: Page):
    page.goto("/ab2023/gsb")

    page.get_by_label("Zoek gemeente").fill("Borsele")
    page.get_by_role("listitem").filter(has_text="Borsele").click()

    expect(page).to_have_url(re.compile(r"/gsb/654-borsele/csb/17-scheldestromen/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Borsele")).to_be_visible()


def test_searching_a_stembureau_submits_on_the_first_match(page: Page):
    page.goto(BORSELE)

    # Unlike the region lists, the stembureau search takes the first suggestion on
    # Enter, so a fragment of the name is enough.
    page.get_by_label("Zoek op naam, adres of stembureau-nummer").fill("Heinkenszand")
    page.get_by_label("Zoek op naam, adres of stembureau-nummer").press("Enter")

    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten stembureau"))).to_be_visible()


def test_the_results_page_serves_the_source_documents(page: Page):
    page.goto(BORSELE_RESULTS)
    expect(page.get_by_role("heading", name="Brondocumenten")).to_be_visible()

    document = page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))
    href = document.get_attribute("href")
    assert re.fullmatch(r"/api/documents/\d+/download/", href or "")

    # Fetching the link rather than clicking it: the download redirects to object
    # storage, which the compose stack and CI publish on different ports.
    assert page.request.get(href).ok


def test_the_results_timeline_can_be_reversed(page: Page):
    page.goto(BORSELE_RESULTS)
    expect(page.get_by_role("heading", name="Hoe zijn de resultaten tot stand gekomen?")).to_be_visible()

    toggle = page.get_by_role("button", name="Laatste stap bovenaan")
    toggle.click()
    expect(page.get_by_role("button", name="Eerste stap bovenaan")).to_be_visible()


def test_the_page_index_jumps_to_the_counting_results(page: Page):
    page.goto(BORSELE_RESULTS)
    expect(page.get_by_text("Op deze pagina:")).to_be_visible()

    page.get_by_role("link", name=re.compile(r"zoals ze meetellen in de officiele uitslag")).click()
    expect(page).to_have_url(re.compile(r"#telresultaten$"))
    expect(page.get_by_role("heading", level=2, name="Telresultaten", exact=True)).to_be_visible()
