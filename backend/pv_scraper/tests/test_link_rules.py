import pytest

from pv_scraper.utils.link_rules import filename_for, is_pv, is_results_context, newest_year


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Uitslag gemeenteraad 2022", 2022),
        ("Verkiezingen 2018 tot en met 2026", 2026),
        ("0717_pv_stembureau_1_veere_tk23.pdf", 2023),
        ("uitslag_gr_22.pdf", 2022),
        # Not inside a word, which "program22" would be; a missed year only means a link is kept.
        ("helvoirtgr26eerstetelling.pdf", None),
        ("GR-2026 stembureau", 2026),
        ("Proces-verbaal stembureau 12", None),
        ("20180321 telefoon 0118-412000", None),
    ],
)
def test_newest_year(text, expected):
    assert newest_year(text) == expected


@pytest.mark.parametrize(
    "context, file_context, expected",
    [
        ("Proces-verbaal Na 31-2", "na31-2.pdf", (True, "")),
        ("Telling stembureau 4", "telling.pdf", (True, "")),
        ("Wijk Centrum Gemeenteraadsverkiezing 2018", "centrum.pdf", (True, "")),
        ("centrum_ps2023.pdf", "centrum_ps2023.pdf", (True, "")),
        ("Kandidatenlijsten Tweede Kamer", "lijsten.pdf", (False, "excluded")),
        ("Garantstelling", "garantstelling.pdf", (False, "excluded")),
        ("Proces-verbaal verkiezingen", "kandidatenlijst.pdf", (False, "excluded")),
        ("Jaarverslag", "jaarverslag.pdf", (False, "no-pv-signal")),
    ],
)
def test_is_pv(context, file_context, expected):
    assert is_pv(context, file_context) == expected


@pytest.mark.parametrize(
    "context, expected",
    [
        ("Processen-verbaal", True),
        ("Uitslag gemeenteraad", True),
        ("Uitslag waterschapsverkiezingen 2019", True),
        ("Uitslag", False),
        ("Verkiezingen", False),
    ],
)
def test_is_results_context(context, expected):
    assert is_results_context(context) == expected


@pytest.mark.parametrize(
    "url, headers, text, expected",
    [
        ("https://x.nl/a/pv%201.pdf", {}, "", "pv 1.pdf"),
        ("https://x.nl/download/123", {}, "Stembureau 1", "Stembureau 1.pdf"),
        ("https://x.nl/d", {"content-disposition": "attachment; filename*=UTF-8''sb%201.pdf"}, "", "sb 1.pdf"),
        ("https://x.nl/d", {"content-disposition": 'attachment; filename="a:b.pdf"'}, "", "a_b.pdf"),
    ],
)
def test_filename_for(url, headers, text, expected):
    assert filename_for(url, headers, text) == expected
