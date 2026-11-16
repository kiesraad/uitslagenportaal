from unittest import mock

import pytesseract
import pytest
from PIL import Image

from pv_ocr.utils.ocr import DPI, letters_only, render_scale, rotate_upright


@pytest.mark.parametrize(
    ("text", "letters"),
    [("2.4 Stemmen per lijst", "stemmenperlijst"), ("Verslag van de zit-\nting", "verslagvandezitting"), ("", "")],
)
def test_letters_only_keeps_lowercase_letters(text, letters):
    assert letters_only(text) == letters


@pytest.mark.parametrize(("width", "height"), [(595, 842), (842, 595)], ids=["portrait", "landscape"])
def test_render_scale_is_the_dpi_scale_for_a4(width, height):
    assert render_scale(width, height) == pytest.approx(DPI / 72, rel=0.01)


def test_render_scale_is_none_for_a_page_over_a3():
    assert render_scale(2000, 3000) is None


def test_render_scale_is_lower_for_a_page_between_a4_and_a3():
    scale = render_scale(842, 1191)

    assert scale is not None
    assert scale < DPI / 72


@pytest.mark.parametrize(("osd", "size"), [({"rotate": 90}, (50, 100)), ({"rotate": 0}, None)])
def test_rotate_upright(osd, size):
    with mock.patch.object(pytesseract, "image_to_osd", return_value=osd):
        rotated = rotate_upright(Image.new("L", (100, 50)))

    assert (rotated.size if rotated else None) == size


def test_rotate_upright_gives_up_when_tesseract_cannot_tell():
    error = pytesseract.TesseractError(1, "Too few characters")
    with mock.patch.object(pytesseract, "image_to_osd", side_effect=error):
        assert rotate_upright(Image.new("L", (100, 50))) is None
