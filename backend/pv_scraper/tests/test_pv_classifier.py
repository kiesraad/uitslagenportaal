from pathlib import Path
from unittest import mock

import pypdfium2 as pdfium
import pytesseract
import pytest
from PIL import Image

from pv_scraper.utils.pv_classifier import DPI, PvClassifier, ResultMatch

N_10_2_TITLE = "Proces-verbaal van een stembureau. Zo telt u hoeveel stemmen elke lijst heeft gekregen"
NA_31_2_TITLE = "Het gemeentelijk stembureau telt de stemmen per kandidaat"


def classifier(name: str = "pv.pdf") -> PvClassifier:
    return PvClassifier(Path(name))


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
            {"gemeente": "0888", "stembureau": "12", "kieskring": "19"},
        ),
        ("Nummer stembureau 602", {"stembureau": "602"}),
        ("Stembureaunummer: nr. 7", {"stembureau": "7"}),
        ("Geen regio", {}),
    ],
)
def test_find_region(text, expected):
    assert PvClassifier.find_region(text) == expected


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
        # A year too far from the election type doesn't belong to it.
        ("gemeenteraad " + "x" * 100 + " 2026", "pv.pdf", ("", "")),
        ("", "stembureau_7.pdf", ("", "")),
    ],
)
def test_find_election(text, name, expected):
    assert classifier(name).find_election(text) == expected


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
    assert result.region == {"gemeente": "0888", "stembureau": "12"}
    assert result.election == ("GR2026", "name")


def test_classify_returns_the_best_supported_pass_when_none_identifies():
    pv = classifier()
    pv.ocr_passes, asked = passes(("crop", "niets"), ("full", "Model N 10-2\nGemeente 888"), ("rotated", "Model X 9"))

    result = pv.classify()

    assert asked == ["crop", "full", "rotated"]
    assert (result.model, result.matched_on, result.found_by) == ("N 10-2", ResultMatch.CODE, "full")
    # Region and election are only read for an identified model.
    assert result.region == {}
    assert result.election == ("", "")


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
