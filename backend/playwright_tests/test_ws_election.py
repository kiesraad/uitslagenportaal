"""Waterschap election (Scheldestromen WS fixture)."""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright


def test_homepage_leads_through_the_waterschappen_list_to_the_party_matrix(page: Page):
    page.goto("/")

    page.get_by_role("link", name="Waterschapsverkiezingen 2023").click()
    expect(page).to_have_url(re.compile(r"/gsb/?$"))
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Waterschappen")).to_be_visible()
    expect(page.get_by_role("link", name="Borsele")).to_be_visible()
    expect(page.get_by_role("link", name="Goes")).to_be_visible()

    page.get_by_role("link", name="Waterschappen").click()
    expect(page).to_have_url(re.compile(r"/csb/?$"))
    expect(page.get_by_role("link", name="Scheldestromen")).to_be_visible()

    page.get_by_role("link", name="Scheldestromen").click()
    expect(page).to_have_url(re.compile(r"/csb/[^/]+/resultaten/?$"))
    expect(page.get_by_role("link", name="Heel waterschap")).to_be_visible()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()

    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page).to_have_url(re.compile(r"/csb/[^/]+/resultaten/[^/]+/?$"))
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    expect(page.get_by_role("heading", level=3, name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Kandidaat")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Totaal")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Borsele")).to_be_visible()


def test_gemeente_list_leads_to_borsele_and_its_party_results(page: Page):
    page.goto("/ab2023/gsb")
    expect(page.get_by_role("link", name="Borsele")).to_be_visible()
    expect(page.get_by_role("link", name="Goes")).to_be_visible()

    page.get_by_role("link", name="Borsele").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Borsele")).to_be_visible()
    expect(page.get_by_role("link", name="Resultaten per stembureau")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_be_visible()
    # "stembureau" or "stembureaus" depending on how many the fixture holds:
    # the heading is an ICU plural, so a single station reads "1 stembureau".
    expect(page.get_by_role("heading", level=2, name=re.compile(r"stembureaus? in Gemeente Borsele"))).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"Heinkenszand"))).to_be_visible()

    page.get_by_role("link", name="Hele gemeente").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/resultaten/?$"))
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()

    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/resultaten/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten gemeente"))).to_be_visible()
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    expect(page.get_by_role("heading", level=3, name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_text(re.compile(r"Minderhoud"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"Totaal stemmen lijst"))).to_be_visible()


def test_csb_per_gemeente_shows_that_goes_has_no_results(page: Page):
    page.goto("/ab2023/csb/17-scheldestromen")
    expect(page.get_by_role("heading", level=1, name="Waterschap - Scheldestromen")).to_be_visible()
    expect(page.get_by_role("link", name="Per gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Borsele")).to_be_visible()
    expect(page.get_by_role("link", name="Goes")).to_be_visible()

    page.get_by_role("link", name="Goes").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/resultaten/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Goes")).to_be_visible()
    expect(page.get_by_role("heading", name="De telresultaten van Goes zijn nog niet gepubliceerd")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_have_count(0)
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_have_count(0)


def test_stembureau_list_leads_to_stembureau_results_and_party_results(page: Page):
    page.goto("/ab2023/gsb/654-borsele/csb/17-scheldestromen")
    expect(page.get_by_role("heading", level=1, name="Gemeente Borsele")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"Heinkenszand"))).to_be_visible()

    page.get_by_role("link", name=re.compile(r"Heinkenszand")).click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten stembureau"))).to_be_visible()
    expect(page.get_by_role("heading", level=2, name="Telresultaten", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()

    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/[^/]+/[^/]+/?$"))
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    expect(page.get_by_role("heading", level=3, name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_text(re.compile(r"Minderhoud"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"Totaal stemmen lijst"))).to_be_visible()
