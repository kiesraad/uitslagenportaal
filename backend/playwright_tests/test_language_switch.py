"""
Language switching.

Smoke test for the NL/EN switcher. The other modules assert on Dutch text and rely
on the pinned `lang=nl` from conftest.py; this one exercises the switch itself
rather than duplicating those suites in English.
"""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright


def test_switching_to_english_changes_the_interface_and_survives_a_reload(page: Page):
    page.goto("/")

    expect(page.locator("html")).to_have_attribute("lang", "nl")
    expect(page.get_by_text("Deze website in andere talen:")).to_be_visible()

    page.get_by_role("button", name="English").click()

    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_text("This website in other languages:")).to_be_visible()
    # The switcher now offers the way back, each language named in its own tongue.
    expect(page.get_by_role("button", name="Nederlands")).to_be_visible()

    # The choice survives a reload, since it is stored rather than kept in the URL.
    page.reload()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_text("This website in other languages:")).to_be_visible()


def test_election_content_is_translated_for_the_active_locale(page: Page):
    page.goto("/")
    page.get_by_role("button", name="English").click()

    page.get_by_role("link", name="Waterschapsverkiezingen 2023").click()
    # Region labels come from the catalogue, not from concatenated fragments.
    expect(page.get_by_role("link", name="Municipality")).to_be_visible()
    expect(page.get_by_role("link", name="Water authorities")).to_be_visible()

    page.get_by_role("link", name="Water authorities").click()
    page.get_by_role("link", name="Scheldestromen").click()
    expect(page.get_by_role("link", name="Entire water authority")).to_be_visible()
    expect(page.get_by_role("heading", name="Counting results")).to_be_visible()
    expect(page.get_by_text("Number of votes")).to_be_visible()
