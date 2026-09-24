"""
Small-screen smoke tests: at 320 CSS px, the WCAG reflow width, no page scrolls sideways.

Wide content such as the vote matrix may scroll, but only inside its own container.
"""

import re

import pytest
from playwright.sync_api import Locator, Page, expect

pytestmark = [
    pytest.mark.playwright,
    pytest.mark.usefixtures("seeded_database"),
    pytest.mark.browser_context_args(viewport={"width": 320, "height": 640}),
]

BORSELE = "/ab2023/gsb/654-borsele/csb/17-scheldestromen"
BORSELE_RESULTS = f"{BORSELE}/resultaten"
SCHELDESTROMEN_RESULTS = "/ab2023/csb/17-scheldestromen/resultaten"

# Reports the page width and the element that sticks out furthest past the viewport.
_OVERFLOW_JS = """() => {
    const root = document.documentElement;
    let widest = null;
    for (const el of document.body.querySelectorAll("*")) {
        const right = el.getBoundingClientRect().right;
        if (right > root.clientWidth && (!widest || right > widest.right)) {
            widest = {right, tag: el.tagName.toLowerCase(), cls: el.getAttribute("class") ?? ""};
        }
    }
    return {scrollWidth: root.scrollWidth, clientWidth: root.clientWidth, widest};
}"""


def expect_no_horizontal_scroll(page: Page) -> None:
    # The h1 marks a rendered page; checking earlier would measure the loading state.
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    result = page.evaluate(_OVERFLOW_JS)
    assert result["scrollWidth"] <= result["clientWidth"], (
        f"page is {result['scrollWidth']}px wide in a {result['clientWidth']}px viewport; "
        f"widest element: {result['widest']}"
    )


def expect_scrolls_within_itself(container: Locator) -> None:
    assert container.evaluate("el => el.scrollWidth > el.clientWidth"), "container does not overflow at all"


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/ab2023/gsb",
        "/ab2023/csb",
        BORSELE,
        BORSELE_RESULTS,
        SCHELDESTROMEN_RESULTS,
        "/ps2023/csb/3-drenthe/resultaten",
        "/ab2023/fout-melden",
        "/onzin",
    ],
)
def test_page_does_not_scroll_sideways(page: Page, path: str):
    page.goto(path)
    expect_no_horizontal_scroll(page)


def test_the_vote_matrix_scrolls_within_itself(page: Page):
    # The matrix of votes per gemeente is only on a party page at waterschap level.
    page.goto(SCHELDESTROMEN_RESULTS)
    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page).to_have_url(re.compile(r"/csb/[^/]+/resultaten/[^/]+/?$"))

    table = page.get_by_role("table").filter(has=page.get_by_role("columnheader", name="Kandidaat"))
    expect(table).to_be_visible()
    expect_no_horizontal_scroll(page)
    expect_scrolls_within_itself(table.locator(".."))

    last_header = table.get_by_role("columnheader").last
    last_header.scroll_into_view_if_needed()
    expect(last_header).to_be_in_viewport()


def test_gemeente_search_works_on_a_small_screen(page: Page):
    page.goto("/ab2023/gsb")

    page.get_by_label("Zoek gemeente").fill("Borsele")
    page.get_by_role("option", name="Borsele").click()

    expect(page).to_have_url(re.compile(r"/gsb/654-borsele/csb/17-scheldestromen/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Borsele")).to_be_visible()
