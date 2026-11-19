"""
The HTML the server sends, before any JavaScript runs.

The other suites drive a browser, so they pass whether a page was rendered on the server or
in the browser. These read the raw response, as a crawler or a link preview does.
"""

import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.playwright, pytest.mark.usefixtures("seeded_database")]

RESULTS = "/ab2023/gsb/654-borsele/csb/17-scheldestromen/resultaten"


def test_a_results_page_arrives_with_its_title_and_counts(page: Page):
    response = page.request.get(RESULTS)

    assert response.status == 200
    html = response.text()
    assert "<title>Resultaten Gemeente Borsele - Kiesraad</title>" in html
    # Formatted as on the page, so it comes from the markup rather than the embedded data.
    assert "10.878" in html


def test_the_lang_cookie_renders_the_page_in_english(page: Page):
    html = page.request.get(RESULTS, headers={"Cookie": "lang=en"}).text()

    assert '<html lang="en"' in html
    assert "<title>Results Municipality of Borsele - Kiesraad</title>" in html


@pytest.mark.parametrize(
    "path",
    ["/onzin/pad/diep", "/ab2023", "/nietbestaand/gsb", f"{RESULTS}/nietbestaand"],
)
def test_a_missing_page_answers_404(page: Page, path: str):
    assert page.request.get(path).status == 404
