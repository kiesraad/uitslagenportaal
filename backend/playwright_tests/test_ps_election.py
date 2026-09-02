"""Provinciale Staten election (Drenthe PS fixture)."""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright


def test_homepage_leads_through_the_provincie_list_to_the_drenthe_party_matrix(page: Page):
    page.goto("/")

    page.get_by_role("link", name="Provinciale Statenverkiezingen 2023").click()
    expect(page).to_have_url(re.compile(r"/gsb/?$"))
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Provincies")).to_be_visible()

    page.get_by_role("link", name="Provincies").click()
    expect(page).to_have_url(re.compile(r"/csb/?$"))
    expect(page.get_by_role("link", name="Drenthe")).to_be_visible()

    page.get_by_role("link", name="Drenthe").click()
    expect(page).to_have_url(re.compile(r"/csb/[^/]+/resultaten/?$"))
    expect(page.get_by_role("link", name="Hele provincie")).to_be_visible()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()

    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(r"/csb/[^/]+/resultaten/[^/]+/?$"))
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    expect(page.get_by_role("heading", level=3, name="VVD")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Kandidaat")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Totaal")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Aa en Hunze")).to_be_visible()


def test_gemeente_list_leads_to_aa_en_hunze_and_its_party_results(page: Page):
    page.goto("/ps2023/gsb")
    expect(page.get_by_role("link", name="Aa en Hunze")).to_be_visible()

    page.get_by_role("link", name="Aa en Hunze").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Aa en Hunze")).to_be_visible()
    expect(page.get_by_role("link", name="Resultaten per stembureau")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_be_visible()
    # "stembureau" or "stembureaus" depending on how many the fixture holds:
    # the heading is an ICU plural, so a single station reads "1 stembureau".
    expect(
        page.get_by_role("heading", level=2, name=re.compile(r"stembureaus? in Gemeente Aa en Hunze"))
    ).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"Gemeentehuis Gieten"))).to_be_visible()

    page.get_by_role("link", name="Hele gemeente").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/resultaten/?$"))
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()

    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/resultaten/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten gemeente"))).to_be_visible()
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    expect(page.get_by_role("heading", level=3, name="VVD")).to_be_visible()
    expect(page.get_by_text(re.compile(r"Meeuwissen-Dekker"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"Totaal stemmen lijst"))).to_be_visible()


def test_stembureau_list_leads_to_stembureau_results_and_party_results(page: Page):
    page.goto("/ps2023/gsb/1680-aa-en-hunze/csb/3-drenthe")
    expect(page.get_by_role("heading", level=1, name="Gemeente Aa en Hunze")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"Gemeentehuis Gieten"))).to_be_visible()

    page.get_by_role("link", name=re.compile(r"Gemeentehuis Gieten")).click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/[^/]+/?$"))
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten stembureau"))).to_be_visible()
    expect(page.get_by_role("heading", level=2, name="Telresultaten", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()

    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(r"/gsb/[^/]+/csb/[^/]+/[^/]+/[^/]+/?$"))
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    expect(page.get_by_role("heading", level=3, name="VVD")).to_be_visible()
    expect(page.get_by_text(re.compile(r"Meeuwissen-Dekker"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"Totaal stemmen lijst"))).to_be_visible()


def test_csb_per_gemeente_lists_the_drenthe_gemeenten(page: Page):
    page.goto("/ps2023/csb/3-drenthe")
    expect(page.get_by_role("heading", level=1, name="Provincie - Drenthe")).to_be_visible()
    expect(page.get_by_role("link", name="Hele provincie")).to_be_visible()
    expect(page.get_by_role("link", name="Per gemeente")).to_be_visible()

    # The gemeenten hang under a kieskring here, but the list is filtered by their CSB.
    page.get_by_role("link", name="Aa en Hunze").click()
    expect(page).to_have_url(re.compile(r"/gsb/1680-aa-en-hunze/csb/3-drenthe/?$"))
    expect(page.get_by_role("heading", level=1, name="Gemeente Aa en Hunze")).to_be_visible()
