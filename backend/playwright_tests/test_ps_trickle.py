"""Provinciale Staten results as each document's data arrives.

Waterschap trickle has no HSB. This one does: the Kieskringen tab appears only after
a 510c, and GSB/HSB/CSB each keep their own telling. States are built with the ORM.
"""

import re

import pytest
from playwright.sync_api import Page, expect

from playwright_tests.trickle import (
    add_aa_en_hunze_telling,
    add_assen_hsb,
    add_drenthe_csb,
    add_ps_candidate_lists,
    ps_definition,
)

pytestmark = [
    pytest.mark.playwright,
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("empty_database"),
]


def expect_ps_tabs_without_hsb(page: Page) -> None:
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Provincies")).to_be_visible()
    expect(page.get_by_role("link", name="Kieskringen")).to_have_count(0)


def expect_ps_tabs_with_hsb(page: Page) -> None:
    expect(page.get_by_role("link", name="Gemeente")).to_be_visible()
    expect(page.get_by_role("link", name="Kieskringen")).to_be_visible()
    expect(page.get_by_role("link", name="Provincies")).to_be_visible()


def expect_unpublished_gemeente(page: Page, name: str) -> None:
    expect(page.get_by_role("heading", level=1, name=f"Gemeente {name}")).to_be_visible()
    expect(page.get_by_role("heading", name=f"De telresultaten van {name} zijn nog niet gepubliceerd")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_have_count(0)
    expect(page.get_by_role("link", name="Resultaten per stembureau")).to_have_count(0)


def expect_unpublished_csb(page: Page) -> None:
    expect(page.get_by_role("heading", name="De telresultaten van Drenthe zijn nog niet gepubliceerd")).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_have_count(0)


def expect_hsb_is_not_found(page: Page) -> None:
    page.goto("/ps2023/hsb")
    expect(page.get_by_role("heading", level=1, name="Pagina niet gevonden")).to_be_visible()


def test_after_definition_lists_show_unpublished_regions(page: Page):
    ps_definition()

    page.goto("/ps2023/gsb")
    expect_ps_tabs_without_hsb(page)
    expect(page.get_by_role("link", name="Aa en Hunze")).to_be_visible()
    expect(page.get_by_role("link", name="Emmen")).to_be_visible()

    page.get_by_role("link", name="Aa en Hunze").click()
    expect_unpublished_gemeente(page, "Aa en Hunze")

    page.goto("/ps2023/gsb")
    page.get_by_role("link", name="Emmen").click()
    expect_unpublished_gemeente(page, "Emmen")

    page.goto("/ps2023/csb")
    expect(page.get_by_role("link", name="Drenthe")).to_be_visible()
    page.get_by_role("link", name="Drenthe").click()
    expect_unpublished_csb(page)

    expect_hsb_is_not_found(page)


def test_after_candidate_lists_results_are_still_unpublished(page: Page):
    ps = ps_definition()
    add_ps_candidate_lists(ps)

    page.goto("/ps2023/gsb")
    expect_ps_tabs_without_hsb(page)
    page.get_by_role("link", name="Aa en Hunze").click()
    expect_unpublished_gemeente(page, "Aa en Hunze")
    expect(page.get_by_role("link", name="VVD")).to_have_count(0)

    page.goto("/ps2023/csb/3-drenthe/resultaten")
    expect_unpublished_csb(page)

    expect_hsb_is_not_found(page)


def test_after_aa_en_hunze_telling_emmen_and_higher_levels_are_still_unpublished(page: Page):
    ps = ps_definition()
    add_ps_candidate_lists(ps)
    add_aa_en_hunze_telling(ps)

    page.goto("/ps2023/gsb")
    expect_ps_tabs_without_hsb(page)
    page.get_by_role("link", name="Aa en Hunze").click()
    expect(page.get_by_role("heading", level=1, name="Gemeente Aa en Hunze")).to_be_visible()
    expect(page.get_by_role("link", name="Resultaten per stembureau")).to_be_visible()
    expect(page.get_by_role("link", name="Hele gemeente")).to_be_visible()
    expect(
        page.get_by_role("heading", level=2, name=re.compile(r"stembureaus? in Gemeente Aa en Hunze"))
    ).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"Gemeentehuis Gieten"))).to_be_visible()
    expect(page.get_by_text("Geplaatst op:")).to_be_visible()

    page.get_by_role("link", name="Hele gemeente").click()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_be_visible()
    expect(page.get_by_role("link", name="CDA")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))).to_be_visible()

    page.goto("/ps2023/gsb")
    page.get_by_role("link", name="Emmen").click()
    expect_unpublished_gemeente(page, "Emmen")

    page.goto("/ps2023/csb/3-drenthe/resultaten")
    expect_unpublished_csb(page)

    expect_hsb_is_not_found(page)


def test_after_assen_hsb_the_kieskring_tab_appears(page: Page):
    ps = ps_definition()
    add_ps_candidate_lists(ps)
    add_aa_en_hunze_telling(ps)
    add_assen_hsb(ps)

    page.goto("/ps2023/gsb")
    expect_ps_tabs_with_hsb(page)

    page.get_by_role("link", name="Kieskringen").click()
    expect(page.get_by_role("link", name="Assen")).to_be_visible()
    page.get_by_role("link", name="Assen").click()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_text("Geplaatst op:")).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510c"))).to_be_visible()

    page.get_by_role("link", name="VVD").click()
    expect(page.get_by_role("columnheader", name="Aa en Hunze")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Emmen")).to_be_visible()

    page.goto("/ps2023/gsb")
    page.get_by_role("link", name="Aa en Hunze").click()
    page.get_by_role("link", name="Hele gemeente").click()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))).to_be_visible()

    page.goto("/ps2023/gsb")
    page.get_by_role("link", name="Emmen").click()
    expect_unpublished_gemeente(page, "Emmen")

    page.goto("/ps2023/csb/3-drenthe/resultaten")
    expect_unpublished_csb(page)


def test_after_drenthe_csb_emmen_stays_unpublished_on_gsb(page: Page):
    ps = ps_definition()
    add_ps_candidate_lists(ps)
    add_aa_en_hunze_telling(ps)
    add_assen_hsb(ps)
    add_drenthe_csb(ps)

    page.goto("/ps2023/csb")
    page.get_by_role("link", name="Drenthe").click()
    expect(page.get_by_role("heading", name="Telresultaten")).to_be_visible()
    expect(page.get_by_text("Geplaatst op:")).to_be_visible()
    expect(page.get_by_role("link", name="VVD")).to_be_visible()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510d"))).to_be_visible()

    page.get_by_role("link", name="VVD").click()
    expect(page.get_by_role("columnheader", name="Aa en Hunze")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Emmen")).to_be_visible()

    page.goto("/ps2023/hsb/1-assen/resultaten")
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510c"))).to_be_visible()

    page.goto("/ps2023/gsb")
    page.get_by_role("link", name="Aa en Hunze").click()
    page.get_by_role("link", name="Hele gemeente").click()
    expect(page.get_by_role("link", name=re.compile(r"EML_NL tellingbestand 510b"))).to_be_visible()

    page.goto("/ps2023/gsb")
    page.get_by_role("link", name="Emmen").click()
    expect_unpublished_gemeente(page, "Emmen")
    expect(page.get_by_role("link", name="VVD")).to_have_count(0)
    expect(page.get_by_text("Geplaatst op:")).to_have_count(0)
