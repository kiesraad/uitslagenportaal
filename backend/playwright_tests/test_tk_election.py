"""Tweede Kamer election: one staat CSB (Nederland) with several kieskringen."""

import re

import pytest
from playwright.sync_api import Page, expect

from playwright_tests.election_states import (
    add_nederland_csb,
    add_rotterdam_hsb,
    add_tk_candidate_lists,
    tk_definition,
)
from playwright_tests.timeline import CHECK, GSB, SB, expect_timeline_steps

# Nederland spans several kieskringen, so only a kieskring's own pages have an HSB step.
CSB_STEPS = ["De Kiesraad publiceert de uitslag", CHECK, GSB, SB]
ROTTERDAM_STEPS = ["De Kiesraad publiceert de uitslag", CHECK, "Optelling kieskring Rotterdam", GSB, SB]

pytestmark = [
    pytest.mark.playwright,
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("empty_database"),
]


def expect_tk_tabs(page: Page) -> None:
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Kieskringen")).to_be_visible()
    expect(page.get_by_role("link", name="Nederland")).to_be_visible()


def open_kieskring(page: Page, name: str) -> None:
    page.goto("/tk2025/hsb")
    page.get_by_role("link", name=name).click()


def expect_unpublished_kieskring(page: Page, name: str) -> None:
    expect(
        page.get_by_role("heading", name=f"De telresultaten van de kieskring {name} zijn nog niet gepubliceerd")
    ).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_have_count(0)


def test_after_definition_kieskringen_and_nederland_are_unpublished(page: Page):
    tk_definition()

    page.goto("/tk2025/gsb")
    expect_tk_tabs(page)

    page.get_by_role("link", name="Kieskringen").click()
    expect(page.get_by_role("link", name="Leiden")).to_be_visible()
    page.get_by_role("link", name="Rotterdam").click()
    expect(page).to_have_url(re.compile(r"/tk2025/hsb/10-rotterdam/resultaten/?$"))
    expect_unpublished_kieskring(page, "Rotterdam")
    expect_timeline_steps(page, ROTTERDAM_STEPS)

    # The kieskring hangs under Nederland, whose gemeenten are listed per CSB.
    page.get_by_role("navigation", name="Kruimelpad").get_by_role("link", name="Nederland").click()
    expect(page).to_have_url(re.compile(r"/tk2025/csb/nederland/?$"))
    expect(page.get_by_role("link", name="Schiedam")).to_be_visible()
    expect(page.get_by_role("link", name="Katwijk")).to_be_visible()

    page.goto("/tk2025/gsb")
    page.get_by_role("link", name="Nederland").click()
    expect(
        page.get_by_role("heading", name="De telresultaten van Nederland zijn nog niet gepubliceerd")
    ).to_be_visible()
    expect_timeline_steps(page, CSB_STEPS)


def test_after_rotterdam_hsb_its_results_are_published(page: Page):
    tk = tk_definition()
    add_tk_candidate_lists(tk)
    add_rotterdam_hsb(tk)

    open_kieskring(page, "Rotterdam")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510c"))).to_be_visible()
    expect_timeline_steps(page, ROTTERDAM_STEPS)
    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(r"/tk2025/hsb/10-rotterdam/resultaten/[^/]+/?$"))
    expect(page.get_by_role("columnheader", name="Schiedam")).to_be_visible()
    expect(page.get_by_role("rowheader", name=re.compile(r"Brekelmans"))).to_have_count(1)
    expect_timeline_steps(page, ROTTERDAM_STEPS)

    open_kieskring(page, "Leiden")
    expect_unpublished_kieskring(page, "Leiden")


def test_after_nederland_csb_the_party_matrix_is_per_kieskring(page: Page):
    tk = tk_definition()
    add_tk_candidate_lists(tk)
    add_rotterdam_hsb(tk)
    add_nederland_csb(tk)

    page.goto("/tk2025/csb")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510d")).first).to_be_visible()
    expect_timeline_steps(page, CSB_STEPS)
    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(r"/tk2025/csb/nederland/resultaten/[^/]+/?$"))
    expect(page.get_by_role("columnheader", name="Leiden")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Rotterdam")).to_be_visible()
    # One row although the candidate has a record on each kieskring's list.
    expect(page.get_by_role("rowheader", name=re.compile(r"Brekelmans"))).to_have_count(1)
    expect_timeline_steps(page, CSB_STEPS)
