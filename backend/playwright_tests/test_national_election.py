"""TK and EP elections: one staat CSB (Nederland) with several kieskringen; only their candidate lists differ."""

import re
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from playwright.sync_api import Page, expect

from playwright_tests.election_states import (
    NationalPortal,
    add_ep_candidate_list,
    add_nederland_csb,
    add_rotterdam_hsb,
    add_tk_candidate_lists,
    ep_definition,
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


@dataclass
class NationalElection:
    slug: str
    definition: Callable[[], NationalPortal]
    add_candidate_lists: Callable[[NationalPortal], None]


@pytest.fixture(
    params=[
        pytest.param(NationalElection("tk2025", tk_definition, add_tk_candidate_lists), id="TK"),
        pytest.param(NationalElection("ep2024", ep_definition, add_ep_candidate_list), id="EP"),
    ]
)
def national(request: pytest.FixtureRequest) -> NationalElection:
    return request.param


def expect_national_tabs(page: Page) -> None:
    expect(page.get_by_role("link", name="Gemeenten")).to_be_visible()
    expect(page.get_by_role("link", name="Kieskringen")).to_be_visible()
    expect(page.get_by_role("link", name="Nederland")).to_be_visible()


def open_kieskring(page: Page, slug: str, name: str) -> None:
    page.goto(f"/{slug}/hsb")
    page.get_by_role("link", name=name).click()


def expect_unpublished_kieskring(page: Page, name: str) -> None:
    expect(
        page.get_by_role("heading", name=f"De telresultaten van de kieskring {name} zijn nog niet gepubliceerd")
    ).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_have_count(0)


def test_after_definition_kieskringen_and_nederland_are_unpublished(page: Page, national: NationalElection):
    national.definition()
    slug = national.slug

    page.goto(f"/{slug}/gsb")
    expect_national_tabs(page)

    page.get_by_role("link", name="Kieskringen").click()
    expect(page.get_by_role("link", name="Leiden")).to_be_visible()
    page.get_by_role("link", name="Rotterdam").click()
    expect(page).to_have_url(re.compile(rf"/{slug}/hsb/10-rotterdam/resultaten/?$"))
    expect_unpublished_kieskring(page, "Rotterdam")
    expect_timeline_steps(page, ROTTERDAM_STEPS)

    # The breadcrumb leads to the same page as the Nederland tab.
    page.get_by_role("navigation", name="Kruimelpad").get_by_role("link", name="Nederland").click()
    expect(page).to_have_url(re.compile(rf"/{slug}/csb/?$"))
    expect(
        page.get_by_role("heading", name="De telresultaten van Nederland zijn nog niet gepubliceerd")
    ).to_be_visible()
    expect_timeline_steps(page, CSB_STEPS)

    # Nederland's gemeenten are listed per CSB, also when they hang under a kieskring.
    page.goto(f"/{slug}/csb/nederland")
    expect(page.get_by_role("link", name="Schiedam")).to_be_visible()
    expect(page.get_by_role("link", name="Katwijk")).to_be_visible()


def test_after_rotterdam_hsb_its_results_are_published(page: Page, national: NationalElection):
    portal = national.definition()
    national.add_candidate_lists(portal)
    add_rotterdam_hsb(portal)

    open_kieskring(page, national.slug, "Rotterdam")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510c"))).to_be_visible()
    expect_timeline_steps(page, ROTTERDAM_STEPS)
    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(rf"/{national.slug}/hsb/10-rotterdam/resultaten/[^/]+/?$"))
    expect(page.get_by_role("columnheader", name="Schiedam")).to_be_visible()
    expect(page.get_by_role("rowheader", name=re.compile(r"Brekelmans"))).to_have_count(1)
    expect_timeline_steps(page, ROTTERDAM_STEPS)

    open_kieskring(page, national.slug, "Leiden")
    expect_unpublished_kieskring(page, "Leiden")


def test_after_nederland_csb_the_party_matrix_is_per_kieskring(page: Page, national: NationalElection):
    portal = national.definition()
    national.add_candidate_lists(portal)
    add_rotterdam_hsb(portal)
    add_nederland_csb(portal)

    # The only CSB: its list page shows its results directly.
    page.goto(f"/{national.slug}/csb")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510d")).first).to_be_visible()
    expect_timeline_steps(page, CSB_STEPS)
    page.get_by_role("link", name="VVD").click()
    expect(page).to_have_url(re.compile(rf"/{national.slug}/csb/nederland/resultaten/[^/]+/?$"))
    expect(page.get_by_role("columnheader", name="Leiden")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Rotterdam")).to_be_visible()
    # One row, also in TK where the candidate has a record on each kieskring's list.
    expect(page.get_by_role("rowheader", name=re.compile(r"Brekelmans"))).to_have_count(1)
    expect_timeline_steps(page, CSB_STEPS)
