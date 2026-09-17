"""The numbers on the results pages are the numbers in the EML fixtures.

The other specs walk navigation. This one reads the telling files with the same
parser the importer uses, then checks that those totals are what the page shows.
"""

import pytest
from playwright.sync_api import Page, expect

from playwright_tests.conftest import EML_FIXTURES
from playwright_tests.eml_counts import (
    CandidateCount,
    PartyCount,
    format_nl,
    rejected_votes,
    reporting_unit_party_counts,
    total_candidate_counts,
    total_counted,
    total_party_counts,
)

pytestmark = [pytest.mark.playwright, pytest.mark.usefixtures("seeded_database")]

WS_510B = EML_FIXTURES / "ws" / "Telling_AB2023_Scheldestromen_gemeente_Borsele.eml.xml"
WS_510D = EML_FIXTURES / "ws" / "Totaaltelling_AB2023_Scheldestromen_waterschap_Scheldestromen.eml.xml"
WS_230B = EML_FIXTURES / "ws" / "Kandidatenlijsten_AB2023_Scheldestromen.eml.xml"
PS_510B = EML_FIXTURES / "ps" / "Telling_PS2023_Drenthe_gemeente_Aa_en_Hunze.eml.xml"
PS_510D = EML_FIXTURES / "ps" / "Totaaltelling_PS2023_Drenthe_provincie_Drenthe.eml.xml"
PS_230B = EML_FIXTURES / "ps" / "Kandidatenlijsten_PS2023_Drenthe.eml.xml"

WS_GSB = "/ab2023/gsb/654-borsele/csb/17-scheldestromen/resultaten"
WS_CSB = "/ab2023/csb/17-scheldestromen/resultaten"
PS_GSB = "/ps2023/gsb/1680-aa-en-hunze/csb/3-drenthe/resultaten"
PS_CSB = "/ps2023/csb/3-drenthe/resultaten"


def party_row_name(party: PartyCount) -> str:
    """Accessible name of a VotesList party link: list number, name, and formatted votes."""
    return f"{party.list_number} {party.name} {format_nl(party.votes)}"


def party_link(page: Page, party: PartyCount):
    return page.get_by_role("link", name=party_row_name(party), exact=True)


def expect_votes_beside(page: Page, label: str, formatted: str) -> None:
    expect(page.get_by_text(label, exact=True).locator("xpath=following-sibling::span[1]")).to_have_text(formatted)


def matrix_footer(page: Page):
    return page.get_by_role("row").filter(has_text="Totaal").last


def expect_party_totals(page: Page, parties: list[PartyCount]) -> None:
    for party in parties:
        if party.votes == 0:
            expect(page.get_by_text(party.name, exact=True)).to_be_visible()
            continue
        expect(party_link(page, party)).to_be_visible()


def expect_candidate_totals(
    page: Page, party: PartyCount, candidates: list[CandidateCount], *, matrix: bool = False
) -> None:
    if matrix:
        expect(matrix_footer(page).get_by_role("cell").nth(1)).to_have_text(format_nl(party.votes))
        for candidate in candidates:
            row = page.get_by_role("row").filter(has_text=candidate.label)
            expect(row.get_by_role("cell").nth(1)).to_have_text(format_nl(candidate.votes))
        return

    expect_votes_beside(page, f"Totaal stemmen lijst {party.list_number}", format_nl(party.votes))
    for candidate in candidates:
        formatted = format_nl(candidate.votes) if candidate.votes else "–"
        expect_votes_beside(page, candidate.label, formatted)


def expect_turnout(page: Page, path) -> None:
    expect_votes_beside(page, "Totaal stemmen op kandidaten", format_nl(total_counted(path)))
    expect_votes_beside(page, "Blanco stemmen", format_nl(rejected_votes(path, "blanco")))
    expect_votes_beside(page, "Ongeldige stemmen", format_nl(rejected_votes(path, "ongeldig")))


@pytest.mark.parametrize(
    ("url", "eml"),
    [
        pytest.param(WS_GSB, WS_510B, id="ws-gsb-510b"),
        pytest.param(PS_GSB, PS_510B, id="ps-gsb-510b"),
        pytest.param(WS_CSB, WS_510D, id="ws-csb-510d"),
        pytest.param(PS_CSB, PS_510D, id="ps-csb-510d"),
    ],
)
def test_party_totals_on_the_results_page_match_the_eml(page: Page, url, eml):
    parties = total_party_counts(eml)

    page.goto(url)
    expect_party_totals(page, parties)
    expect_turnout(page, eml)


@pytest.mark.parametrize(
    ("url", "eml_510", "eml_230"),
    [
        pytest.param(WS_GSB, WS_510B, WS_230B, id="ws-gsb"),
        pytest.param(PS_GSB, PS_510B, PS_230B, id="ps-gsb"),
        pytest.param(WS_CSB, WS_510D, WS_230B, id="ws-csb"),
        pytest.param(PS_CSB, PS_510D, PS_230B, id="ps-csb"),
    ],
)
def test_candidate_totals_on_the_party_page_match_the_eml(page: Page, url, eml_510, eml_230):
    party = total_party_counts(eml_510)[0]
    candidates = total_candidate_counts(eml_510, eml_230, party.list_number)

    page.goto(url)
    party_link(page, party).click()
    expect_candidate_totals(page, party, candidates, matrix=url in (WS_CSB, PS_CSB))


def test_stembureau_party_totals_match_the_eml(page: Page):
    parties = reporting_unit_party_counts(WS_510B, "Heinkenszand")

    page.goto("/ab2023/gsb/654-borsele/csb/17-scheldestromen")
    page.get_by_role("link", name="Heinkenszand").click()
    expect_party_totals(page, parties)


@pytest.mark.parametrize(
    ("url", "eml", "gemeente"),
    [
        pytest.param(WS_CSB, WS_510D, "Borsele", id="ws-borsele"),
        pytest.param(PS_CSB, PS_510D, "Aa en Hunze", id="ps-aa-en-hunze"),
    ],
)
def test_csb_matrix_totals_match_the_eml(page: Page, url, eml, gemeente):
    party = total_party_counts(eml)[0]
    unit = next(p for p in reporting_unit_party_counts(eml, gemeente) if p.list_number == party.list_number)

    page.goto(url)
    party_link(page, party).click()

    footer = matrix_footer(page)
    expect(footer.get_by_role("cell").nth(1)).to_have_text(format_nl(party.votes))
    column = page.get_by_role("columnheader").all_inner_texts().index(gemeente)
    expect(footer.get_by_role("cell").nth(column)).to_have_text(format_nl(unit.votes))
