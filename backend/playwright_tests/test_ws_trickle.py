"""Waterschap results as each document's data arrives.

The other Playwright modules import a finished election. This one starts empty and
checks the portal after each pause, so unpublished gemeenten and a CSB that is still
waiting stay in good order. States are built with the ORM, not by importing EML.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from election.models import ElectionCategory
from playwright_tests.trickle import (
    GR_LABEL,
    PS_LABEL,
    TK_LABEL,
    WS_LABEL,
    add_borsele_telling,
    add_candidate_lists,
    add_csb_totaaltelling,
    add_home_timeline,
    expired_config,
    visible_config,
    ws_definition,
)

pytestmark = [
    pytest.mark.playwright,
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("empty_database"),
]


def expect_ws_tabs_without_hsb(page: Page) -> None:
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Waterschappen")).to_be_visible()
    expect(page.get_by_role("link", name="Kieskringen")).to_have_count(0)


def expect_unpublished_gemeente(page: Page, name: str) -> None:
    expect(page.get_by_role("heading", level=1, name=f"Gemeente {name}")).to_be_visible()
    expect(page.get_by_role("heading", name=f"De telresultaten van {name} zijn nog niet gepubliceerd")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_have_count(0)
    expect(page.get_by_role("link", name="Resultaten per stembureau")).to_have_count(0)


def expect_unpublished_csb(page: Page) -> None:
    expect(
        page.get_by_role("heading", name="De telresultaten van Scheldestromen zijn nog niet gepubliceerd")
    ).to_be_visible()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_have_count(0)


def expect_empty_region_lists(page: Page) -> None:
    page.goto("/ab2023/gsb")
    expect_ws_tabs_without_hsb(page)
    expect(page.get_by_role("heading", name="De gemeenten zijn nog niet beschikbaar")).to_be_visible()

    page.get_by_role("link", name="Waterschappen").click()
    expect(page.get_by_role("heading", name="De waterschappen zijn nog niet beschikbaar")).to_be_visible()


def home_election_link(page: Page, label: str):
    # The single-election home page also links “Bekijk de tellingen … voor {label}”.
    return page.get_by_role("link", name=label, exact=True)


def test_home_with_no_election_shows_coming_soon(page: Page):
    page.goto("/")
    expect(page.get_by_role("heading", name="Telresultaten volgen binnenkort")).to_be_visible()
    expect(home_election_link(page, WS_LABEL)).to_have_count(0)
    expect(page.get_by_role("heading", name="Hoe komt de uitslag tot stand?")).to_have_count(0)


def test_one_election_config_has_empty_region_lists_and_a_timeline(page: Page):
    config = visible_config(identifier="AB2023", label=WS_LABEL, category=ElectionCategory.WS.value)
    add_home_timeline(config)

    page.goto("/")
    expect(home_election_link(page, WS_LABEL)).to_be_visible()
    expect(page.get_by_role("heading", name="Hoe komt de uitslag tot stand?")).to_be_visible()

    home_election_link(page, WS_LABEL).click()
    expect_empty_region_lists(page)


def test_two_election_configs_hide_the_timeline_and_expired_elections(page: Page):
    visible_config(identifier="AB2023", label=WS_LABEL, category=ElectionCategory.WS.value)
    visible_config(identifier="PS2023", label=PS_LABEL, category=ElectionCategory.PS.value)
    expired_config(identifier="GR2026", label=GR_LABEL, category=ElectionCategory.GR.value)
    expired_config(identifier="TK2025", label=TK_LABEL, category=ElectionCategory.TK.value)

    page.goto("/")
    expect(home_election_link(page, WS_LABEL)).to_be_visible()
    expect(home_election_link(page, PS_LABEL)).to_be_visible()
    expect(home_election_link(page, GR_LABEL)).to_have_count(0)
    expect(home_election_link(page, TK_LABEL)).to_have_count(0)
    expect(page.get_by_role("heading", name="Hoe komt de uitslag tot stand?")).to_have_count(0)

    home_election_link(page, WS_LABEL).click()
    expect_empty_region_lists(page)

    page.goto("/")
    home_election_link(page, PS_LABEL).click()
    expect(page.get_by_role("heading", name="De gemeenten zijn nog niet beschikbaar")).to_be_visible()

    page.goto("/gr2026/gsb")
    expect(page.get_by_role("heading", level=1, name="Pagina niet gevonden")).to_be_visible()


def test_after_definition_lists_show_unpublished_regions(page: Page):
    ws_definition()

    page.goto("/ab2023/gsb")
    expect_ws_tabs_without_hsb(page)
    expect(page.get_by_role("link", name="Borsele")).to_be_visible()
    expect(page.get_by_role("link", name="Goes")).to_be_visible()

    page.get_by_role("link", name="Borsele").click()
    expect_unpublished_gemeente(page, "Borsele")

    page.goto("/ab2023/gsb")
    page.get_by_role("link", name="Goes").click()
    expect_unpublished_gemeente(page, "Goes")

    page.goto("/ab2023/csb")
    expect(page.get_by_role("link", name="Scheldestromen")).to_be_visible()
    page.get_by_role("link", name="Scheldestromen").click()
    expect_unpublished_csb(page)


def test_after_candidate_lists_results_are_still_unpublished(page: Page):
    ws = ws_definition()
    add_candidate_lists(ws)

    page.goto("/ab2023/gsb")
    page.get_by_role("link", name="Borsele").click()
    expect_unpublished_gemeente(page, "Borsele")
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_have_count(0)

    page.goto("/ab2023/csb/17-scheldestromen/resultaten")
    expect_unpublished_csb(page)


def test_after_borsele_telling_goes_and_csb_are_still_unpublished(page: Page):
    ws = ws_definition()
    add_candidate_lists(ws)
    add_borsele_telling(ws)

    page.goto("/ab2023/gsb")
    page.get_by_role("link", name="Borsele").click()
    expect(page.get_by_role("heading", level=1, name="Gemeente Borsele")).to_be_visible()
    expect(page.get_by_role("link", name="Resultaten per stembureau")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_be_visible()
    expect(page.get_by_role("heading", level=2, name=re.compile(r"stembureaus? in Gemeente Borsele"))).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"Heinkenszand"))).to_be_visible()
    expect(page.get_by_text("Geplaatst op:")).to_be_visible()

    page.get_by_role("link", name="Hele gemeente").click()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))).to_be_visible()

    page.goto("/ab2023/gsb")
    page.get_by_role("link", name="Goes").click()
    expect_unpublished_gemeente(page, "Goes")

    page.goto("/ab2023/csb/17-scheldestromen/resultaten")
    expect_unpublished_csb(page)


def test_after_csb_totaaltelling_goes_stays_unpublished(page: Page):
    ws = ws_definition()
    add_candidate_lists(ws)
    add_borsele_telling(ws)
    add_csb_totaaltelling(ws)

    page.goto("/ab2023/csb")
    page.get_by_role("link", name="Scheldestromen").click()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_text("Geplaatst op:")).to_be_visible()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("heading", name="Brondocumenten")).to_be_visible()

    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page.get_by_role("columnheader", name="Borsele")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Goes")).to_be_visible()

    page.goto("/ab2023/gsb")
    page.get_by_role("link", name="Borsele").click()
    page.get_by_role("link", name="Hele gemeente").click()
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))).to_be_visible()
    expect(page.get_by_role("heading", name="Brondocumenten")).to_be_visible()

    page.goto("/ab2023/gsb")
    page.get_by_role("link", name="Goes").click()
    expect_unpublished_gemeente(page, "Goes")
    expect(page.get_by_role("link", name="Partij voor Zeeland")).to_have_count(0)
    expect(page.get_by_text("Geplaatst op:")).to_have_count(0)
