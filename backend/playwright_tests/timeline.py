"""
Assertions on the election timeline ("Hoe zijn de resultaten tot stand gekomen?").
The components have unit tests; the election tests use these to check that each page hands its timeline the region
and variant from the API. Only titles and order are asserted: the status suffix of a step depends on today's date.
"""

import re

from playwright.sync_api import Locator, Page, expect

STATUS = r", (afgerond|bezig|nog niet gestart)$"

CHECK = "Centraal Stembureau controleert"
GSB = "Optelling per gemeente"
SB = "Telling in de stembureaus"


def timeline(page: Page) -> Locator:
    return page.locator("#results-timeline")


def expect_timeline_steps(page: Page, titles: list[str]) -> None:
    """The step headings in the default order (last step first), each with its sr-only status."""
    headings = timeline(page).get_by_role("heading", level=3)
    expect(headings).to_have_text([re.compile(f"^{re.escape(title)}{STATUS}") for title in titles])
