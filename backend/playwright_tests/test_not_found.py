"""
The paths that end on the not-found page.

Three mechanisms lead here — the catch-all routes, a loader whose election does not
exist, and a party that is missing from a region's results — and all three render the
same page, so each test only has to prove which one it took to get there.
"""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright


def expect_not_found(page: Page) -> None:
    expect(page.get_by_role("heading", level=1, name="Pagina niet gevonden")).to_be_visible()
    expect(page.get_by_role("link", name="Homepage")).to_be_visible()


def test_an_unknown_path_shows_the_not_found_page(page: Page):
    page.goto("/onzin/pad/diep")
    expect_not_found(page)


def test_an_election_root_shows_the_not_found_page(page: Page):
    # An election has no landing page of its own; it starts at /gsb or /csb.
    page.goto("/ab2023")
    expect_not_found(page)


def test_an_unknown_election_shows_the_not_found_page(page: Page):
    # The loader's 404 reaches the error boundary, which reduces it to a not-found.
    page.goto("/nietbestaand/gsb")
    expect_not_found(page)


def test_an_unknown_party_shows_the_not_found_page(page: Page):
    page.goto("/ab2023/gsb/654-borsele/csb/17-scheldestromen/resultaten/nietbestaand")
    expect_not_found(page)


def test_the_not_found_page_leads_home(page: Page):
    page.goto("/ab2023/onzin")

    page.get_by_role("link", name="Homepage").click()
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_role("link", name="Waterschapsverkiezingen 2023")).to_be_visible()
