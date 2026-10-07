import datetime
import io
from unittest import mock

import pypdfium2 as pdfium
import pytesseract
import pytest
from django.core.files.storage import default_storage
from PIL import Image
from pypdf import PdfReader

from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from pv_scraper.tests.factories import ScrapeSourceFactory
from pv_scraper.utils.pv_classifier import (
    DPI,
    ClassificationResult,
    PvClassificationException,
    PvClassifier,
    PvElection,
    PvRegion,
    ResultMatch,
    model_token,
)

N_10_2_TITLE = "Proces-verbaal van een stembureau. Zo telt u hoeveel stemmen elke lijst heeft gekregen"
NA_31_2_TITLE = "Het gemeentelijk stembureau telt de stemmen per kandidaat"


def classifier(name: str = "pv.pdf") -> PvClassifier:
    return PvClassifier(NamedBytesIO(b"", name))


def test_result_match_members_are_ordered_best_first():
    assert ResultMatch.members() == [
        ResultMatch.CODE_TITLE,
        ResultMatch.TITLE,
        ResultMatch.CODE,
        ResultMatch.CONFLICT,
        ResultMatch.UNKNOWN,
        ResultMatch.NONE,
    ]


@pytest.mark.parametrize(
    ("matched_on", "certain"),
    [
        (ResultMatch.CODE_TITLE, True),
        (ResultMatch.TITLE, True),
        (ResultMatch.CODE, False),
        (ResultMatch.CONFLICT, False),
        (ResultMatch.UNKNOWN, False),
        (ResultMatch.NONE, False),
    ],
)
def test_result_match_is_certain(matched_on, certain):
    assert matched_on.is_certain() is certain


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Model N 10-2", ["N 10-2"]),
        ("Model P 2a", ["P 2a"]),
        # OCR misreads letters as digits and the other way round.
        ("Modei N I0-z", ["N 10-2"]),
        ("ModelNa31-2", ["Na 31-2"]),
        # A look-alike followed by a space is the letter I.
        ("Model 1 1", ["I 1"]),
        # Without its letters a number counts only when a single known model has it.
        ("Model 31-1", ["Na 31-1"]),
        ("Model 22", ["22"]),
        ("Model N 10-1 en Model Na 14-2", ["N 10-1", "Na 14-2"]),
        ("Geen modelcode", []),
    ],
)
def test_find_codes(text, expected):
    assert PvClassifier.find_codes(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (N_10_2_TITLE, ["N 10-2"]),
        # Spacing, hyphenation and case don't matter.
        ("HOEVEEL STEM-\nMEN ELKE LIJST HEEFT GE KREGEN", ["N 10-2"]),
        # A misread letter still matches.
        ("hoeveel stemmen elke Iijst heeft gekregen", ["N 10-2"]),
        # Both titles match here; the longer one wins.
        (
            "Verslagen van tellingen van stembureaus die zijn herteld door het gemeentelijk stembureau",
            ["Na 14-2 Bijlage 1"],
        ),
        # A misread title of another PV next to an exact title is text that merely resembles it.
        (N_10_2_TITLE + "\nCorrigendum van een gemeentelijk stembureeu", ["N 10-2"]),
        (NA_31_2_TITLE + "\nBijlage 1 - verslag telling stembureau", ["Na 31-2", "Na 31-2 Bijlage 1"]),
        ("Proces-verbaal van een stembureau", []),
    ],
)
def test_find_titles(text, expected):
    assert PvClassifier.find_titles(text) == expected


@pytest.mark.parametrize(
    ("text", "model", "matched_on"),
    [
        ("Model N 10-2\n" + N_10_2_TITLE, "N 10-2", ResultMatch.CODE_TITLE),
        (N_10_2_TITLE, "N 10-2", ResultMatch.TITLE),
        ("Model N 10-2", "N 10-2", ResultMatch.CODE),
        # The bijlage title decides over the repeated title of its PV.
        (
            "Model Na 31-2\n" + NA_31_2_TITLE + "\nBijlage 1 - verslag telling stembureau",
            "Na 31-2 Bijlage 1",
            ResultMatch.CODE_TITLE,
        ),
        ("Model N 10-1\n" + N_10_2_TITLE, None, ResultMatch.CONFLICT),
        (N_10_2_TITLE + "\n" + NA_31_2_TITLE, None, ResultMatch.CONFLICT),
        ("Model X 99", None, ResultMatch.UNKNOWN),
        ("Geen model", None, ResultMatch.NONE),
    ],
)
def test_identify_model(text, model, matched_on):
    result = classifier().identify_model(text)

    assert (result.model, result.matched_on) == (model, matched_on)


def test_identify_model_keeps_what_ocr_found():
    result = classifier().identify_model("Model N 10-2\n" + N_10_2_TITLE)

    assert result.codes == ["N 10-2"]
    assert result.titles == ["N 10-2"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Gemeente: 888\nStembureau: 12\nKieskring 19",
            {"code": "0888", "stembureau": "12", "kieskring": "19"},
        ),
        ("Nummer stembureau 602", {"stembureau": "602"}),
        ("Stembureaunummer: nr. 7", {"stembureau": "7"}),
        ("Stembureau-nr. 210", {"stembureau": "210"}),
        ("Stembureau Nr: 33", {"stembureau": "33"}),
        ("1659 Laarbeek\nCentraal Stembureau", {"code": "1659", "name": "Laarbeek"}),
        ("373 Bergen (NH)\nGemeentelijk stembureau", {"code": "0373", "name": "Bergen (NH)"}),
        ("Stembureau 17\n\nBrummen\nStembureau 17", {"name": "Brummen", "stembureau": "17"}),
        ("Moerdijk\nStembureau\nNummer: 19", {"name": "Moerdijk", "stembureau": "19"}),
        ("Gemeente Velsen\nStembureau-nr. 19", {"name": "Velsen", "stembureau": "19"}),
        (
            "Gemeente 0899 Brunssum Stembureau 13",
            {"code": "0899", "name": "Brunssum", "stembureau": "13"},
        ),
        (
            "Gemeente 0762 Deurne — Stembureau 10",
            {"code": "0762", "name": "Deurne", "stembureau": "10"},
        ),
        ("Gemeente 0762 Deurne -", {"code": "0762", "name": "Deurne"}),
        ("Deurne -\nStembureau 10", {"name": "Deurne", "stembureau": "10"}),
        ("Edam-Volendam\nStembureau 1", {"name": "Edam-Volendam", "stembureau": "1"}),
        (
            "0796 's-Hertogenbosch\nGemeentelijk stembureau",
            {"code": "0796", "name": "'s-Hertogenbosch"},
        ),
        ("’s-Gravenhage\nStembureau 3", {"name": "’s-Gravenhage", "stembureau": "3"}),
        (
            "Gemeente: 888\n1659 Laarbeek\nCentraal Stembureau",
            {"code": "0888", "name": "Laarbeek"},
        ),
        ("verslag van het gemeentelijk\nstembureau.", {}),
        ("Details van het stembureau\nStembureau 32", {"stembureau": "32"}),
        ("1659 Laarbeek", {}),
        ("5741 AB Beek en Donk", {}),
        ("73E9 F1DD A095\n3372 3063 B838 CF21", {}),
        ("18 maart 2026\n2026 Verkiezing", {}),
        ("Geen regio", {}),
    ],
)
def test_find_region(text, expected):
    assert PvClassifier.find_region(text) == PvRegion(**expected)


@pytest.mark.parametrize(
    ("text", "name", "expected"),
    [
        ("de leden van de gemeenteraad van Brummen op 18 maart 2026", "pv.pdf", ("GR2026", "pdf")),
        ("Tweede Kamer der Staten-Generaal in\nmaart 2021", "pv.pdf", ("TK2021", "pdf")),
        ("De verkiezing van de leden van TK25", "pv.pdf", ("TK2025", "pdf")),
        # The text wins over the file name.
        ("Verkiezing Gemeenteraad 2026", "tk25.pdf", ("GR2026", "pdf")),
        ("", "helvoirtgr26eerstetelling.pdf", ("GR2026", "name")),
        ("", "Lelystad_uitkomst_tk-2025.pdf", ("TK2025", "name")),
        # A waterschap election is AB, also when it is written as WS.
        ("Algemeen bestuur van het waterschap De Dommel 2023", "pv.pdf", ("AB2023", "pdf")),
        ("", "proces_verbaal_ws2023_rivierenland.pdf", ("AB2023", "name")),
        ("", "N11_AB2019_DeDommel.pdf", ("AB2019", "name")),
        ("Uitslag WS23", "pv.pdf", ("AB2023", "pdf")),
        # The header wins over the rest of the text.
        (
            "Verkiezing Gemeenteraad 2026 woensdag 18 maart 2026\nVerslag en telresultaten per lijst - Model N 10-2\n"
            "Tweede Kamer 2025",
            "pv.pdf",
            ("GR2026", "header"),
        ),
        # A year too far from the election type doesn't belong to it.
        ("gemeenteraad " + "x" * 100 + " 2026", "pv.pdf", ("", "")),
        ("", "stembureau_7.pdf", ("", "")),
    ],
)
def test_find_election(text, name, expected):
    election = classifier(name).find_election(text)

    assert (election.id, election.found_in) == expected


MARCH_18 = datetime.date(2026, 3, 18)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (
            "Brunssum\nStembureau 10\nVerkiezing Gemeenteraad 2026 woensdag 18 maart 2026",
            PvElection("GR2026", MARCH_18, "", "header"),
        ),
        (
            "0755 Boekel\nCentraal Stembureau\nDe verkiezing van de leden van de gemeenteraad\n18 maart 2026",
            PvElection("GR2026", MARCH_18, "", "header"),
        ),
        (
            "Helmond Stembureau De verkiezing van de leden van de gemeenteraad van Helmond woensdag 18 maart 2026",
            PvElection("GR2026", MARCH_18, "Helmond", "header"),
        ),
        ("Gemeenteraad Purmerend 2026 18 maart 2026", PvElection("GR2026", MARCH_18, "Purmerend", "header")),
        # The date may wrap.
        (
            "De verkiezing van de leden van de gemeenteraad van Ede van 18\nmaart 2026",
            PvElection("GR2026", MARCH_18, "Ede", "header"),
        ),
        (
            "Verkiezing Gemeenteraad 2026 woensdag 18 maart\n2026Verslag en telresultaten per lijst",
            PvElection("GR2026", MARCH_18, "", "header"),
        ),
        # So may the label.
        (
            "De verkiezing van de leden van het algemeen bestuur van het\nwaterschap Aa en Maas 15 maart 2027",
            PvElection("AB2027", datetime.date(2027, 3, 15), "Aa en Maas", "header"),
        ),
        (
            "Verkiezing van de leden van het algemeen bestuur van het Hoogheemraadschap van Delfland 15 maart 2027",
            PvElection("AB2027", datetime.date(2027, 3, 15), "Delfland", "header"),
        ),
        (
            "De verkiezing van de leden van provinciale staten van Drenthe 15 maart 2027",
            PvElection("PS2027", datetime.date(2027, 3, 15), "Drenthe", "header"),
        ),
        (
            "De verkiezing van de leden van de Tweede Kamer der Staten-Generaal woensdag 29 oktober 2025",
            PvElection("TK2025", datetime.date(2025, 10, 29), "", "header"),
        ),
        (
            "Verkiezing Europees Parlement 2024 donderdag 6 juni 2024",
            PvElection("EP2024", datetime.date(2024, 6, 6), "", "header"),
        ),
        # OCR splits words and misreads letters.
        (
            "Stembureou l0\nI Verkiezing Gemeentera ad 2026 woensdag 18 ma art.2026",
            PvElection("GR2026", MARCH_18, "", "header"),
        ),
        (
            "De verkiezing van de leden van de gemeenteraad van | Brummen\n18 maarl2o26",
            PvElection("GR2026", MARCH_18, "Brummen", "header"),
        ),
        # Without a readable day the election still counts.
        (
            "Verkiezing Gemeentera ad 2026 woensdag 1 B ma art 2026",
            PvElection("GR2026", None, "", "header"),
        ),
        ("Verkiezing Gemeenteraad 2026", PvElection("GR2026", None, "", "header")),
        # A date without an election type is not an election.
        ("Brunssum\nStembureau 10\n18 maart 2026", None),
        ("Brunssum\nStembureau 10", None),
    ],
)
def test_find_header_election(header, expected):
    text = header + "\nVerslag en telresultaten per lijst - Model N 10-2\nDe verkiezing van de Tweede Kamer 2025"

    assert PvClassifier.find_header_election(text) == expected


@pytest.mark.parametrize(
    ("election_type", "label", "authority"),
    [
        ("GR", "Verkiezing Gemeenteraad 2026", ""),
        ("GR", "De verkiezing van de leden van de gemeenteraad", ""),
        ("GR", "Gemeenteraadsverkiezing", ""),
        ("GR", "Verkiezing voor de gemeenteraad", ""),
        ("GR", "de verkiezing van de leden van de gemeenteraad van Etten-Leur", "Etten-Leur"),
        ("GR", "de verkiezing van de leden van de gemeenteraad van | Brummen", "Brummen"),
        ("GR", "Gemeenteraad Purmerend 2026", "Purmerend"),
        ("GR", "Gemeenteraad Bergen (NH) 2026", "Bergen (NH)"),
        # A year or a "d.d." ends the name; the date itself was cut off before.
        ("GR", "Verkiezing Gemeenteraad 2026 woensdag 18 maart", ""),
        ("GR", "De verkiezing van de leden van de gemeenteraad van Castricum d.d", "Castricum"),
        ("TK", "De verkiezing van de leden van de Tweede Kamer der Staten-Generaal", ""),
        ("TK", "Verkiezing Tweede Kamer 2025", ""),
        ("TK", "Tweede Kamer der Staten-Generaal 2025", ""),
        ("PS", "De verkiezing van de leden van provinciale staten van Drenthe", "Drenthe"),
        ("PS", "Verkiezing Provinciale Staten Zuid-Holland 2027", "Zuid-Holland"),
        ("PS", "Provinciale Statenverkiezing", ""),
        ("PS", "Provinciale Staten Noord-Brabant 2027", "Noord-Brabant"),
        ("AB", "De verkiezing van de leden van het algemeen bestuur van het waterschap Aa en Maas", "Aa en Maas"),
        (
            "AB",
            "Verkiezing van de leden van het algemeen bestuur van het Hoogheemraadschap van Delfland",
            "Delfland",
        ),
        ("AB", "De verkiezing van de leden van het bestuur van het waterschap Fryslân in", "Fryslân"),
        ("AB", "Algemeen bestuur van het wetterskip Fryslân 2027", "Fryslân"),
        ("AB", "Waterschapsverkiezing", ""),
        (
            "AB",
            "Algemeen bestuur van het hoogheemraadschap van Schieland en de Krimpenerwaard 2027",
            "Schieland en de Krimpenerwaard",
        ),
        ("EP", "De verkiezing van de leden van het Europees Parlement", ""),
        ("EP", "Europees Parlement 2024", ""),
    ],
)
def test_find_authority(election_type, label, authority):
    assert PvClassifier.find_authority(election_type, label) == authority


def test_find_header_election_needs_a_model_code():
    assert PvClassifier.find_header_election("Verkiezing Gemeenteraad 2026 woensdag 18 maart 2026") is None


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("stembureau_7_mfc_de_kloek_zonder_handtekeningen", "7"),
        ("Stembureau 703 GSB", "703"),
        ("Drechterland_stembureau-5_Cultureel-Centrum-Oosterblokker_GR26", "5"),
        ("sb35_1", "35"),
        ("1945_stembureau_103_tvossenhol_hr26_zh", "103"),
        ("1680_Bijlagen 1 en 2_Stembureau_22_Gemeenschapshuis Oes Stee Anderen", "22"),
        ("Brunssum_10_Verenigingsgebouw_de_Burcht_GR26_eerste_telling", "10"),
        ("Altena_08_Dorpshuis_Genderen_GR26", "8"),
        ("Barneveld_5__Goede_Herderkerk_I_GR26_eerste_telling", "5"),
        ("Maastricht_17_TK25", "17"),
        ("20260318-aal-anker-gr26_0", ""),
        ("Stede-Broec_Het-Postkantoor-2_GR26", ""),
        ("20-Dorpshuis-t-Skrale-End", ""),
        ("Bijlage_1_Verslagen", ""),
        ("Lelystad_uitkomst_tk-2025", ""),
        ("Gasbedrijf2", ""),
        # The "<gemeente>_<nummer>_" form wins over a stembureau in the location's name.
        ("Hoorn_24_MFA De Kreek stembureau 1 GR26", "24"),
        # Stembureaus are numbered from 1.
        ("gr2026_18032026_n10-2_23._mobiel_stembureau_0", ""),
    ],
)
def test_find_stembureau_in_name(stem, expected):
    assert PvClassifier.find_stembureau_in_name(stem) == expected


EDE_COVER = (
    "Gemeente 228 Ede\n\nBijlage 1 — verslag telling stembureau\nStembureau 891\n\nBijlage 1\n\nVerslagen van tellingen"
)
EDE_SECTION = (
    "Bijlage 1 — verslag telling stembureau Gemeente 228 Ede\nStembureau 891\n\nStembureau 12\nCultura\n\n"
    "Over deze bijlage"
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (EDE_SECTION, "12"),
        ("Stembureau 7\n'’t Hoekje\n", "7"),
        # A running header is followed by another heading, not by a name.
        (EDE_COVER, ""),
        ("Stembureau 891\n\nOver deze bijlage", ""),
        ("Gemeente 0289 Wageningen Stembureau 13\n\nBijlage 1", ""),
    ],
)
def test_find_section_stembureau(text, expected):
    assert PvClassifier.find_section_stembureau(text) == expected


def passes(*texts):
    """OCR passes that yield the given texts and record how many were asked for."""
    asked = []

    def ocr_passes():
        for found_by, text in texts:
            asked.append(found_by)
            yield found_by, text

    return ocr_passes, asked


def test_classify_stops_at_the_first_identifying_pass():
    pv = classifier("beek_12_gr26.pdf")
    identified = "Model N 10-2\n" + N_10_2_TITLE + "\nGemeente 888\nStembureau 12"
    pv.ocr_passes, asked = passes(("crop", "Model N 10-2"), ("full", identified), ("rotated", "unused"))

    result = pv.classify()

    assert asked == ["crop", "full"]
    assert (result.model, result.matched_on, result.found_by) == ("N 10-2", ResultMatch.CODE_TITLE, "full")
    assert result.text == identified
    assert result.region == PvRegion(code="0888", stembureau="12")
    assert result.election == PvElection("GR2026", found_in="name")


@pytest.mark.parametrize(
    ("text", "stembureau"),
    [
        # A stembureau model takes its number from the file name when OCR misses it,
        ("Model N 10-2\n" + N_10_2_TITLE, "12"),
        # but not over the number OCR read,
        ("Model N 10-2\n" + N_10_2_TITLE + "\nStembureau 3", "3"),
        # and not for a model of the whole gemeente.
        ("Model Na 31-2\n" + NA_31_2_TITLE, ""),
    ],
)
def test_classify_takes_the_stembureau_from_the_file_name(text, stembureau):
    pv = classifier("Beek_12_Gemeenschapshuis_GR26.pdf")
    pv.ocr_passes, _ = passes(("full", text))

    assert pv.classify().region.stembureau == stembureau


BIJLAGE_1 = "Model Na 31-2\n" + NA_31_2_TITLE + "\nBijlage 1 - verslag telling stembureau\n"


@pytest.mark.parametrize(
    ("page1", "page2", "stembureau"),
    [
        # Behind a cover page whose running header names the wrong stembureau, the section on page 2 names it.
        (BIJLAGE_1 + EDE_COVER, EDE_SECTION, "12"),
        # A section on page 1 is enough.
        (BIJLAGE_1 + EDE_SECTION, None, "12"),
        # Without a section heading the running header counts.
        (BIJLAGE_1 + "Stembureau 891", "Over deze bijlage", "891"),
    ],
)
def test_classify_takes_the_stembureau_of_a_bijlage_from_its_section(page1, page2, stembureau):
    pv = classifier("bijlage.pdf")
    pv.ocr_passes, _ = passes(("full", page1))
    with mock.patch.object(pv, "page_text", return_value=page2) as page_text:
        result = pv.classify()

    assert (result.model, result.region.stembureau) == ("Na 31-2 Bijlage 1", stembureau)
    assert page_text.called is (page2 is not None)


def test_classify_returns_the_best_supported_pass_when_none_identifies():
    pv = classifier()
    pv.ocr_passes, asked = passes(("crop", "niets"), ("full", "Model N 10-2\nGemeente 888"), ("rotated", "Model X 9"))

    result = pv.classify()

    assert asked == ["crop", "full", "rotated"]
    assert (result.model, result.matched_on, result.found_by) == ("N 10-2", ResultMatch.CODE, "full")
    # Region and election are only read for an identified model.
    assert result.region == PvRegion()
    assert result.election == PvElection()


def test_ocr_passes_add_the_second_page_to_the_full_first_page():
    pv = classifier()
    first, second = Image.new("L", (100, 100)), Image.new("L", (100, 100))
    texts = {id(first): "eerste", id(second): "tweede"}
    with (
        mock.patch.object(pv, "render_page", side_effect=[first, second]),
        mock.patch.object(pv, "rotate_upright", return_value=None),
        mock.patch.object(pv, "ocr", side_effect=lambda image: texts.get(id(image), "bovenkant")),
    ):
        result = list(pv.ocr_passes())

    assert result == [("crop", "bovenkant"), ("full", "eerste"), ("page2", "eerste\ntweede")]


def test_ocr_passes_read_a_rotated_scan_and_skip_a_missing_second_page():
    pv = classifier()
    page, upright = Image.new("L", (100, 100)), Image.new("L", (100, 100))
    with (
        mock.patch.object(pv, "render_page", side_effect=[page, None]),
        mock.patch.object(pv, "rotate_upright", return_value=upright),
        mock.patch.object(pv, "ocr", side_effect=lambda image: "rechtop" if image is upright else "scheef"),
    ):
        result = list(pv.ocr_passes())

    assert [found_by for found_by, _ in result] == ["crop", "full", "rotated"]
    assert result[2] == ("rotated", "rechtop")


@pytest.mark.parametrize(("osd", "size"), [({"rotate": 90}, (50, 100)), ({"rotate": 0}, None)])
def test_rotate_upright(osd, size):
    with mock.patch.object(pytesseract, "image_to_osd", return_value=osd):
        rotated = PvClassifier.rotate_upright(Image.new("L", (100, 50)))

    assert (rotated.size if rotated else None) == size


def test_rotate_upright_gives_up_when_tesseract_cannot_tell():
    error = pytesseract.TesseractError(1, "Too few characters")
    with mock.patch.object(pytesseract, "image_to_osd", side_effect=error):
        assert PvClassifier.rotate_upright(Image.new("L", (100, 50))) is None


def test_render_page(tmp_path):
    path = tmp_path / "pv.pdf"
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(72, 144)
    pdf.save(path)
    pdf.close()

    pv = PvClassifier(path)
    page = pv.render_page(0)

    assert page.size == (DPI, 2 * DPI)
    assert page.mode == "L"
    assert pv.render_page(1) is None


@pytest.mark.parametrize(
    ("model", "token"),
    [("N 10-2", "N10-2"), ("Na 31-2", "Na31-2"), ("Na 31-2 Bijlage 1", "Na31-2-B1"), ("P 2a", "P2a"), ("I 1", "I1")],
)
def test_model_token(model, token):
    assert model_token(model) == token


@pytest.mark.parametrize(
    ("election_type", "name", "known"),
    [
        ("AB", "Frysl�n", "Fryslân"),
        ("AB", "van Rijnland", ""),
        ("AB", "Vallei en Velowe", "Vallei en Veluwe"),
        ("PS", "Zuid Holland", "Zuid-Holland"),
        ("PS", "Atlantis", ""),
    ],
)
def test_known_authority(election_type, name, known):
    assert PvClassifier.known_authority(election_type, name) == known


@pytest.mark.parametrize(
    ("authority", "name", "expected"),
    [
        ("Aa en Maas", "Aa en Maas", True),
        # Case, spacing and accents don't matter, nor does one misread letter in a longer name.
        ("Fryslân", "Frysl�n", True),
        ("Etten-Leur", "etten leur", True),
        ("Vallei en Veluwe", "Vallei en Velowe", True),
        ("Veluwe", "Vallei en Veluwe", False),
        ("Ede", "Edam", False),
    ],
)
def test_authority_matches(authority, name, expected):
    assert PvClassifier.authority_matches(authority, name) is expected


def blank_pdf(width: int = 72) -> bytes:
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(width, 72)
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    return buffer.getvalue()


BLANK_PDF = blank_pdf()


def classified(model: str, election: PvElection, region: PvRegion, name: str = "pv.pdf") -> PvClassifier:
    pv = PvClassifier(NamedBytesIO(BLANK_PDF, name))
    pv.result = ClassificationResult(model, ResultMatch.CODE_TITLE, region=region, election=election)
    return pv


EDE_12 = PvRegion(code="228", name="Ede", stembureau="12")


@pytest.mark.parametrize(
    ("model", "election", "region", "name"),
    [
        ("N 10-2", PvElection("GR2026"), EDE_12, "GR2026_N10-2_0228-ede_SB12.pdf"),
        # The CSB of a GR election is the gemeente itself, so it is left out.
        ("N 10-2", PvElection("GR2026", authority="Ede"), EDE_12, "GR2026_N10-2_0228-ede_SB12.pdf"),
        # Only a stembureau model names a stembureau.
        ("Na 31-2", PvElection("GR2026"), EDE_12, "GR2026_Na31-2_0228-ede.pdf"),
        ("Na 31-2 Bijlage 1", PvElection("GR2026"), EDE_12, "GR2026_Na31-2-B1_0228-ede_SB12.pdf"),
        ("N 10-1", PvElection("AB2027", authority="Fryslân"), EDE_12, "AB2027_N10-1_fryslan_0228-ede_SB12.pdf"),
        ("Na 31-1", PvElection("PS2027"), PvRegion(name="Bergen (NH)"), "PS2027_Na31-1_bergen-nh.pdf"),
        ("Na 31-1", PvElection("TK2025"), PvRegion(code="1680"), "TK2025_Na31-1_1680.pdf"),
        (
            "N 10-2",
            PvElection("AB2027", authority="Fryslân"),
            PvRegion(code="1900", name="Súdwest-Fryslân", stembureau="5"),
            "AB2027_N10-2_fryslan_1900-sudwest-fryslan_SB5.pdf",
        ),
    ],
)
def test_storage_name(model, election, region, name):
    assert classified(model, election, region).storage_name() == name


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Ede", "ede"),
        ("Súdwest-Fryslân", "sudwest-fryslan"),
        ("'s-Hertogenbosch", "s-hertogenbosch"),
        ("’s-Gravenhage", "s-gravenhage"),
        ("Hunze en Aa's", "hunze-en-aas"),
        ("Amstel, Gooi en Vecht", "amstel-gooi-en-vecht"),
        ("Bergen (NH)", "bergen-nh"),
        ("Edam-Volendam ", "edam-volendam"),
        ("Gooi_en_Vecht", "gooi-en-vecht"),
    ],
)
def test_slug(name, slug):
    assert PvClassifier.slug(name) == slug


def test_storage_name_takes_the_names_it_is_given():
    pv = classified("N 10-2", PvElection("AB2027"), PvRegion(code="0229", name="Edde", stembureau="12"))

    assert pv.storage_name("Vallei en Veluwe", "0228", "Ede") == "AB2027_N10-2_vallei-en-veluwe_0228-ede_SB12.pdf"


@pytest.mark.parametrize(
    ("model", "election", "region"),
    [
        (None, PvElection("GR2026"), EDE_12),
        ("N 10-2", PvElection(), EDE_12),
        ("N 10-2", PvElection("GR2026"), PvRegion()),
    ],
)
def test_storage_name_needs_model_election_and_gemeente(model, election, region):
    with pytest.raises(PvClassificationException):
        classified(model, election, region).storage_name()


@pytest.mark.parametrize(
    ("file_name", "stembureau", "agrees"),
    [
        ("Ede_12_Cultura_GR26.pdf", "12", True),
        ("Ede_12_Cultura_GR26.pdf", "891", False),
        ("pv.pdf", "891", True),
    ],
)
def test_storage_name_needs_the_pv_and_its_file_name_to_agree_on_the_stembureau(file_name, stembureau, agrees):
    region = PvRegion(code="0228", name="Ede", stembureau=stembureau)
    pv = classified("Na 31-2 Bijlage 1", PvElection("GR2026"), region, file_name)

    if agrees:
        assert pv.storage_name() == f"GR2026_Na31-2-B1_0228-ede_SB{stembureau}.pdf"
    else:
        with pytest.raises(PvClassificationException):
            pv.storage_name()


@pytest.mark.django_db
@pytest.mark.parametrize("region", [PvRegion(code="0228", stembureau="12"), PvRegion(name="ede", stembureau="12")])
def test_save_to_storage_names_the_gemeente_as_its_source_does(region):
    source = ScrapeSourceFactory(code="gm0228", name="Ede")

    key = classified("N 10-2", PvElection("GR2026"), region).save_to_storage(source, "pvs")

    assert key == "pvs/GR2026_N10-2_0228-ede_SB12.pdf"
    assert PdfReader(default_storage.open(key)).metadata["/PvGemeenteName"] == "Ede"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("election", "region"),
    [
        (PvElection("GR2026"), PvRegion(code="0289", name="Wageningen")),
        # A GR header naming another gemeente.
        (PvElection("GR2026", authority="Tiel"), EDE_12),
    ],
)
def test_save_to_storage_refuses_a_pv_of_another_gemeente(election, region):
    source = ScrapeSourceFactory(code="gm0228", name="Ede")

    with pytest.raises(PvClassificationException):
        classified("N 10-2", election, region).save_to_storage(source, "pvs")


@pytest.mark.django_db
def test_save_to_storage_takes_the_csb_from_a_waterschap_source():
    source = ScrapeSourceFactory(code="ws0665", kind=RegionCategory.WATERSCHAP, name="Vallei en Veluwe")

    key = classified("N 10-2", PvElection("AB2027"), EDE_12).save_to_storage(source, "pvs")

    assert key == "pvs/AB2027_N10-2_vallei-en-veluwe_0228-ede_SB12.pdf"


@pytest.mark.django_db
def test_save_to_storage_replaces_a_file_of_the_same_name():
    source = ScrapeSourceFactory(code="gm0228", name="Ede")
    classified("N 10-2", PvElection("GR2026"), EDE_12).save_to_storage(source, "pvs")
    newer = classified("N 10-2", PvElection("GR2026"), EDE_12)
    newer_pdf = blank_pdf(width=100)
    newer.file = NamedBytesIO(newer_pdf, "pv.pdf")

    key = newer.save_to_storage(source, "pvs")

    assert default_storage.listdir("pvs")[1] == ["GR2026_N10-2_0228-ede_SB12.pdf"]
    assert default_storage.open(key).read().startswith(newer_pdf)


def test_with_metadata_adds_what_the_pv_is_and_keeps_the_original_bytes():
    election = PvElection("AB2027", datetime.date(2027, 3, 17), "Vallei en Veluwe")
    pv = classified("Na 31-2 Bijlage 1", election, PvRegion(code="228", name="Ede", stembureau="12"))

    content = pv.with_metadata().getvalue()

    assert content.startswith(BLANK_PDF)
    assert {key: value for key, value in PdfReader(io.BytesIO(content)).metadata.items() if key != "/CreationDate"} == {
        "/Creator": "PDFium",
        "/Title": "Na31-2-B1 Ede stembureau 12",
        "/Subject": "AB2027 Vallei en Veluwe",
        "/PvElection": "AB2027",
        "/PvElectionDate": "2027-03-17",
        "/PvModel": "Na31-2-B1",
        "/PvCsb": "Vallei en Veluwe",
        "/PvGemeenteCode": "0228",
        "/PvGemeenteName": "Ede",
        "/PvStembureau": "12",
        "/PvMatchedOn": "code+title",
    }


def test_with_metadata_leaves_out_what_is_unknown():
    pv = classified("Na 31-1", PvElection("GR2026"), PvRegion(name="Súdwest-Fryslân"))

    metadata = PdfReader(pv.with_metadata()).metadata

    assert (metadata["/Title"], metadata["/Subject"], metadata["/PvGemeenteName"]) == (
        "Na31-1 Súdwest-Fryslân",
        "GR2026",
        "Súdwest-Fryslân",
    )
    assert not {"/PvElectionDate", "/PvCsb", "/PvGemeenteCode", "/PvStembureau"} & set(metadata)
