"""Reporting an error in the counting results (Scheldestromen WS fixture)."""

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.playwright

BORSELE_RESULTS = "/ab2023/gsb/654-borsele/csb/17-scheldestromen/resultaten"


def test_results_page_leads_to_the_report_issue_page(page: Page):
    page.goto(BORSELE_RESULTS)

    page.get_by_role("link", name=re.compile(r"Meld een fout of iets dat niet klopt")).click()
    expect(page).to_have_url(re.compile(r"/ab2023/fout-melden/?$"))
    expect(page.get_by_role("heading", level=1, name="Een fout melden")).to_be_visible()
    expect(page.get_by_role("heading", level=2, name="Waarvoor kunt u een melding maken?")).to_be_visible()
    expect(page.get_by_role("heading", level=2, name="Wat wordt er met een melding gedaan?")).to_be_visible()
    expect(page.get_by_role("heading", level=2, name="Punten waar uw melding aan moet voldoen")).to_be_visible()


def test_report_issue_page_links_back_through_its_breadcrumb(page: Page):
    page.goto("/ab2023/fout-melden")
    expect(page.get_by_role("link", name="Home", exact=True)).to_be_visible()

    page.get_by_role("link", name="Waterschapsverkiezingen 2023").click()
    expect(page).to_have_url(re.compile(r"/ab2023/gsb/?$"))
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()


def test_report_issue_page_states_the_reporting_window(page: Page):
    page.goto("/ab2023/fout-melden")

    expect(page.get_by_text(re.compile(r"Een melding aan het centraal stembureau kan van"))).to_be_visible()
    # The button loses its href once the deadline has passed, so it is not a link then;
    # the countdown heading above it moves with the clock too. Both are left unasserted
    # so the test fails on a regression rather than on a date.
    expect(page.get_by_text("Meld een fout", exact=True)).to_be_visible()
