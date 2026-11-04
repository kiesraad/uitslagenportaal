"""Gemeenteraad election (Westerwolde): the gemeente is its own CSB, so its pages have no CSB in the URL."""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright

_seeded = pytest.mark.usefixtures("seeded_database")

PARTY = "Gemeentebelangen Westerwolde"


@_seeded
def test_gemeente_tab_leads_to_westerwolde_its_stembureau_and_party_results(page: Page):
    page.goto("/")
    page.get_by_role("link", name="Gemeenteraadsverkiezingen 2026", exact=True).click()
    expect(page).to_have_url(re.compile(r"/gsb/?$"))
    tabs = page.get_by_role("navigation", name="Subnavigatie")
    expect(tabs.locator('a[href$="/gsb"]')).to_be_visible()
    expect(tabs.locator('a[href$="/csb"]')).to_be_visible()

    page.get_by_role("link", name="Westerwolde").click()
    expect(page).to_have_url(re.compile(r"/gsb/1950-westerwolde/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Westerwolde")).to_be_visible()

    page.get_by_role("link", name=re.compile(r"Verenigingsgebouw De Sprankel")).click()
    expect(page).to_have_url(re.compile(r"/gsb/1950-westerwolde/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten stembureau"))).to_be_visible()

    page.get_by_role("link", name=PARTY).click()
    expect(page.get_by_role("heading", level=3, name=PARTY)).to_be_visible()
    expect(page.get_by_text(re.compile(r"Luth"))).to_be_visible()

    page.goto("/gr2026/gsb/1950-westerwolde/resultaten")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b")).first).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510d"))).to_have_count(0)


@_seeded
def test_csb_tab_leads_to_the_totaaltelling_of_westerwolde(page: Page):
    page.goto("/gr2026/csb")
    page.get_by_role("link", name="Westerwolde").click()
    expect(page).to_have_url(re.compile(r"/csb/1950-westerwolde/resultaten/?$"))
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510d")).first).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL resultaatbestand 520")).first).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))).to_have_count(0)

    page.get_by_role("link", name=PARTY).click()
    expect(page).to_have_url(re.compile(r"/csb/1950-westerwolde/resultaten/[^/]+/?$"))
    expect(page.get_by_role("heading", level=3, name=PARTY)).to_be_visible()
    expect(page.get_by_role("columnheader", name="Totaal")).to_be_visible()
