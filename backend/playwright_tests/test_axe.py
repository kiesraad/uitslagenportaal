"""Axe-core scans of one of each page kind."""

import re

import pytest
from playwright.sync_api import Page, expect

from playwright_tests.axe import assert_no_axe_violations, format_violations, scan
from playwright_tests.election_states import (
    add_rotterdam_hsb,
    add_tk_candidate_lists,
    tk_definition,
)

pytestmark = pytest.mark.axe

_seeded = pytest.mark.usefixtures("seeded_database")

BORSELE = "/ab2023/gsb/654-borsele/csb/17-scheldestromen"
BORSELE_RESULTS = f"{BORSELE}/resultaten"
CSB = "/ab2023/csb/17-scheldestromen"
CSB_RESULTS = f"{CSB}/resultaten"


def _wait_for_h1(page: Page) -> None:
    expect(page.get_by_role("heading", level=1)).to_be_visible()


@_seeded
@pytest.mark.parametrize(
    "url",
    [
        pytest.param("/", id="home"),
        pytest.param("/ab2023/van-stem-tot-uitslag", id="timeline"),
        pytest.param("/ab2023/gsb", id="gsb-list"),
        pytest.param("/ab2023/csb", id="csb-list"),
        pytest.param(CSB, id="csb-gemeenten"),
        pytest.param(CSB_RESULTS, id="csb-results"),
        pytest.param(BORSELE, id="gemeente"),
        pytest.param(BORSELE_RESULTS, id="gemeente-results"),
        pytest.param("/ab2023/fout-melden", id="fout-melden"),
        pytest.param("/onzin/pad/diep", id="not-found"),
    ],
)
def test_seeded_page_has_no_axe_violations(page: Page, url: str):
    page.goto(url)
    _wait_for_h1(page)
    assert_no_axe_violations(page)


@_seeded
def test_csb_party_results_have_no_axe_violations(page: Page):
    page.goto(CSB_RESULTS)
    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    assert_no_axe_violations(page)


@_seeded
def test_gemeente_party_results_have_no_axe_violations(page: Page):
    page.goto(BORSELE_RESULTS)
    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    assert_no_axe_violations(page)


@_seeded
def test_stembureau_results_have_no_axe_violations(page: Page):
    page.goto(BORSELE)
    page.get_by_role("link", name=re.compile(r"Heinkenszand")).click()
    expect(page.get_by_role("heading", level=1, name=re.compile(r"Telresultaten stembureau"))).to_be_visible()
    assert_no_axe_violations(page)


@_seeded
def test_stembureau_party_results_have_no_axe_violations(page: Page):
    page.goto(BORSELE)
    page.get_by_role("link", name=re.compile(r"Heinkenszand")).click()
    page.get_by_role("link", name="Partij voor Zeeland").click()
    expect(page.get_by_role("heading", name=re.compile(r"Telresultaten lijst"))).to_be_visible()
    assert_no_axe_violations(page)


@_seeded
def test_unpublished_gemeente_has_no_axe_violations(page: Page):
    page.goto(CSB)
    page.get_by_role("link", name="Goes").click()
    expect(
        page.get_by_role("heading", name="De telresultaten van de gemeente Goes zijn nog niet gepubliceerd")
    ).to_be_visible()
    assert_no_axe_violations(page)


@_seeded
def test_gemeente_search_suggestions_have_no_axe_violations(page: Page):
    page.goto("/ab2023/gsb")
    page.get_by_label("Zoek gemeente").fill("Borsele")
    expect(page.get_by_role("option", name="Borsele")).to_be_visible()
    assert_no_axe_violations(page)


@_seeded
def test_english_home_has_no_axe_violations(page: Page):
    page.goto("/")
    page.get_by_role("button", name="English").click()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    _wait_for_h1(page)
    assert_no_axe_violations(page)


def _record_violations(page: Page, reports: list[str]) -> None:
    results = scan(page)
    if results.get("violations"):
        reports.append(format_violations(results))


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("empty_database")
def test_hsb_pages_have_no_axe_violations(page: Page):
    """The EML seed has no election with HSBs, so a TK kieskring and its 510c are built here."""
    tk = tk_definition()
    add_tk_candidate_lists(tk)
    add_rotterdam_hsb(tk)

    reports: list[str] = []

    page.goto("/tk2025/hsb")
    _wait_for_h1(page)
    _record_violations(page, reports)

    page.goto("/tk2025/hsb/10-rotterdam")
    _wait_for_h1(page)
    _record_violations(page, reports)

    page.goto("/tk2025/hsb/10-rotterdam/resultaten")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510c"))).to_be_visible()
    _record_violations(page, reports)

    page.get_by_role("link", name="VVD").click()
    expect(page.get_by_role("columnheader", name="Schiedam")).to_be_visible()
    _record_violations(page, reports)

    if reports:
        raise AssertionError("\n\n".join(reports))
