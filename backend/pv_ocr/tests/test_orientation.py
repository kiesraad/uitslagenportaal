from unittest import mock

import numpy as np
import pytesseract
import pytest

from pv_ocr.utils.orientation import osd_rotation, turn, upright

# A4 at 300 dpi, as render_page gives it.
WIDTH, HEIGHT = 2481, 3508
OSD = "pv_ocr.utils.orientation.pytesseract.image_to_osd"


def blank_page() -> np.ndarray:
    page = np.full((HEIGHT, WIDTH), 254, np.uint8)
    page[:100] = 0
    return page


@pytest.mark.parametrize(("rotate", "turned"), [(180, True), (0, False)])
def test_upright(rotate, turned):
    page = blank_page()
    with mock.patch(OSD, return_value={"rotate": rotate, "orientation_conf": 5}) as osd:
        result = upright(page)

    assert bool(result[-1].mean() == 0) == turned
    # An upright page is only checked at half resolution.
    assert osd.call_count == (2 if turned else 1)


def test_upright_keeps_a_page_turned_at_half_resolution_only():
    page = blank_page()
    half, full = {"rotate": 180, "orientation_conf": 1.7}, {"rotate": 0, "orientation_conf": 12}
    with mock.patch(OSD, side_effect=[half, full]) as osd:
        result = upright(page)

    assert result[0].mean() == 0
    assert osd.call_args_list[1].args[0].size == page.shape[::-1]


@pytest.mark.parametrize(
    "osd",
    [{"return_value": {"rotate": 180, "orientation_conf": 0.8}}, {"side_effect": pytesseract.TesseractError(1, "")}],
    ids=["unsure", "error"],
)
def test_osd_rotation_leaves_the_page_when_unsure(osd):
    with mock.patch(OSD, **osd):
        assert osd_rotation(blank_page()) == 0


def test_turn_turns_clockwise():
    page = blank_page()

    result = turn(page, 90)

    assert result.shape == (WIDTH, HEIGHT)
    assert result[:, -1].mean() == 0


def test_turn_leaves_the_page_for_another_angle():
    page = blank_page()

    assert turn(page, 45) is page
