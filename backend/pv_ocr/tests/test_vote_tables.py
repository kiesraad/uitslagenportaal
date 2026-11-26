from unittest import mock

import cv2
import numpy as np
import pytest

from pv_ocr.utils.vote_tables import (
    BorderedTableDetector,
    CountFieldDetector,
    GrayColumnDetector,
    Line,
    column_line,
    description_field,
    in_order,
    is_blank,
    main_column,
    right_column,
    rotate,
    split_merged_rows,
)

# A4 at 300 dpi, as render_page gives it.
WIDTH, HEIGHT = 2481, 3508
ROW = 84


def blank_page() -> np.ndarray:
    return np.full((HEIGHT, WIDTH), 254, np.uint8)


def write(page: np.ndarray, text: str, x: int, y: int, colour: int = 0):
    cv2.putText(page, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.4, colour, 4)


def test_gray_column_detector_finds_a_row_per_printed_candidate_number():
    page = blank_page()
    left, top, width, rows = 900, 700, 100, 12
    page[top : top + rows * ROW, left : left + width] = 180
    for row in range(rows):
        write(page, str(row + 1), left + 20, top + row * ROW + 60)
    # The table's thin right border.
    page[top : top + rows * ROW, left + width + 220 : left + width + 223] = 150

    _, tables = GrayColumnDetector().detect(page)

    assert len(tables) == 1
    assert len(tables[0]) == rows
    x, y, w, _ = tables[0][0]
    assert x == left + width
    assert w == pytest.approx(220, abs=4)
    assert y == pytest.approx(top, abs=2)


def test_gray_column_detector_ignores_a_page_without_a_gray_column():
    page = blank_page()
    write(page, "Lijst 1", 200, 300)

    _, tables = GrayColumnDetector().detect(page)

    assert tables == []


def draw_bordered_table(page: np.ndarray, columns: list[int], top: int, rows: int):
    bottom = top + rows * ROW
    for x in columns:
        page[top:bottom, x : x + 3] = 0
    for y in range(top, bottom + 1, ROW):
        page[y : y + 3, columns[0] : columns[-1] + 3] = 0


def test_bordered_table_detector_takes_the_last_four_boxes_of_each_table():
    page = blank_page()
    # Name, number and four digit boxes; the second table holds fewer rows.
    draw_bordered_table(page, [150, 700, 780, 860, 940, 1020, 1100], 600, 25)
    draw_bordered_table(page, [1250, 1800, 1880, 1960, 2040, 2120, 2200], 600, 11)

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25, 11]
    x, _, w, h = tables[0][0]
    assert x == pytest.approx(780, abs=2)
    assert w == pytest.approx(323, abs=3)
    assert h == pytest.approx(ROW, abs=3)
    assert tables[1][0][0] == pytest.approx(1880, abs=2)


def test_bordered_table_detector_keeps_a_line_broken_by_handwriting():
    page = blank_page()
    draw_bordered_table(page, [150, 700, 780, 860, 940, 1020, 1100], 600, 25)
    # More than a subtotal row apart, so the pieces stay separate lines.
    page[1300:1700, 860:863] = 254

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25]
    assert tables[0][0][0] == pytest.approx(780, abs=2)


def test_bordered_table_detector_keeps_a_row_with_a_dash_across_it():
    page = blank_page()
    draw_bordered_table(page, [150, 700, 780, 860, 940, 1020, 1100], 600, 25)
    # A dash for 0 across the digit boxes of row 17.
    page[600 + 16 * ROW + 40 : 600 + 16 * ROW + 44, 790:1095] = 0

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25]
    assert tables[0][17][1] == pytest.approx(600 + 17 * ROW, abs=3)


def test_bordered_table_detector_passes_over_printed_original_boxes():
    page = blank_page()
    # Name, number, four boxes for the original count and four for the corrected one.
    draw_bordered_table(page, [150, 660, 780, 860, 940, 1020, 1100, 1130, 1210, 1290, 1370, 1450], 600, 25)

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25]
    assert tables[0][0][0] == pytest.approx(1130, abs=2)


def test_bordered_table_detector_passes_over_narrower_original_boxes():
    page = blank_page()
    # Name, number, four narrow boxes for the original count and, a little further, four wide ones for the corrected.
    draw_bordered_table(page, [150, 600, 640, 680, 720, 760], 600, 25)
    draw_bordered_table(page, [810, 870, 930, 990, 1050], 600, 25)

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25]
    assert tables[0][0][0] == pytest.approx(810, abs=2)


def test_bordered_table_detector_drops_the_subtotal_boxes_below_a_table():
    page = blank_page()
    draw_bordered_table(page, [150, 700, 780, 860, 940, 1020, 1100], 600, 25)
    draw_bordered_table(page, [150, 780, 860, 940, 1020, 1100], 600 + 26 * ROW, 1)

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25]


def test_bordered_table_detector_keeps_a_left_table_close_to_the_next():
    page = blank_page()
    # The right table has no name column, only candidate numbers before its boxes.
    draw_bordered_table(page, [150, 700, 780, 860, 940, 1020, 1100], 600, 25)
    draw_bordered_table(page, [1300, 1380, 1460, 1540, 1620, 1700], 600, 25)

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25, 25]


@pytest.mark.parametrize("degrees", [0.5, -0.5])
def test_bordered_table_detector_measures_the_skew_next_to_a_gray_column(degrees):
    page = blank_page()
    # The candidate numbers in a gray column, whose right edge is the first line of the digit boxes.
    page[600 : 600 + 25 * ROW, 700:780] = 170
    draw_bordered_table(page, [150, 700, 780, 860, 940, 1020, 1100], 600, 25)
    page = rotate(page, degrees)
    detector = BorderedTableDetector()

    assert detector.skew(page, detector.anchors(page)[0]) == pytest.approx(degrees, abs=0.05)


def test_bordered_table_detector_ends_the_boxes_at_a_wider_column():
    page = blank_page()
    # Original and corrected boxes sharing a line, and the border of the next table further on.
    draw_bordered_table(page, [150, 660, 720, 780, 840, 900, 960, 1020, 1080, 1140, 1200], 600, 25)
    page[600 : 600 + 25 * ROW, 1300:1303] = 0

    _, tables = BorderedTableDetector().detect(page)

    assert [len(table) for table in tables] == [25]
    assert tables[0][0][0] == pytest.approx(960, abs=2)


@pytest.mark.parametrize(
    ("words", "field"),
    [
        (["Stempassen"], "A"),
        (["Totaal", "toegelaten", "kiezers", "(A+B)"], "D"),
        (["Totaal", "lijst", "12", "-", "CDA"], "E.12"),
        (["Totaal", "lijst", "l2", "-", "CDA"], "E.12"),
        (["Aantal", "méér", "getelde", "stemmen"], "I"),
        (["Aantal", "minder", "getelde", "stemmen"], "J"),
        (["Tel", "het", "aantal", "geldige", "stempassen"], None),
        # "Totaal" misread against its black box.
        (["Frea", "toegelaten", "kiezers", "(A+B)"], "D"),
        (["free", "stemmen", "op", "kandidaten"], "E"),
        (["Jp", "ren", "uitgebrachte", "stemmen", "(E+F+G)"], "H"),
        (["toegelaten", "kiezers", "opnieuw", "geteld?"], None),
        (["Uitgebrachte", "stemmen"], None),
    ],
)
def test_description_field(words, field):
    assert description_field(words) == field


def test_in_order_drops_a_field_read_out_of_order():
    fields = ["A", "B", "D"]
    # The instruction above the counts also mentions volmachtbewijzen.
    candidates = [("A", Line(670, 30, 500, None)), ("B", Line(540, 30, 850, None)), ("B", Line(760, 30, 500, None))]
    candidates.append(("D", Line(900, 30, 500, None)))

    assert [(field, line.top) for field, line in in_order(candidates, fields)] == [("A", 670), ("B", 760), ("D", 900)]


def test_count_field_detector_ends_the_area_at_the_label_box():
    page = blank_page()
    # A gray A box and a black D box, with the descriptions starting right of them.
    page[800 : 800 + ROW, 600:700] = 200
    page[1000 : 1000 + ROW, 600:700] = 20
    lines = [("A", Line(820, 40, 720, None)), ("D", Line(1020, 40, 720, None))]

    with mock.patch.object(CountFieldDetector, "read_lines", return_value=lines):
        areas = CountFieldDetector().detect(page, ["A", "B", "D"])

    assert [field for field, _ in areas] == ["A", "D"]
    for _, (x, y, w, h) in areas:
        assert x + w == pytest.approx(600, abs=10)
        assert w == pytest.approx(CountFieldDetector.COUNT_WIDTH * WIDTH, abs=10)


def test_count_field_detector_takes_a_black_box_cut_by_its_label_as_one():
    page = blank_page()
    # A black I box, its white label running across the middle half of its height.
    page[800 : 800 + ROW, 600:720] = 20
    page[815 : 800 + ROW - 15, 655:663] = 254
    lines = [("I", Line(820, 40, 740, None))]

    with mock.patch.object(CountFieldDetector, "read_lines", return_value=lines):
        ((_, (x, _, w, _)),) = CountFieldDetector().detect(page, ["I"])

    assert x + w == pytest.approx(600, abs=10)


@pytest.mark.parametrize(
    "stroke",
    [
        # A thick 1 in the first box, which blurs into something like gray fill.
        (420, 436),
        # A 1 against the left line of the first box, and one in the last.
        (410, 418),
        (625, 632),
    ],
)
def test_count_field_detector_takes_the_digit_boxes_over_handwriting(stroke):
    page = blank_page()
    for x in (400, 460, 520, 580, 640):
        page[800 : 800 + ROW, x : x + 3] = 0
    page[800 : 800 + ROW, 640:740] = 200
    page[810 : 800 + ROW - 10, stroke[0] : stroke[1]] = 120
    lines = [("A", Line(820, 40, 760, None))]

    with mock.patch.object(CountFieldDetector, "read_lines", return_value=lines):
        ((_, (x, _, _, _)),) = CountFieldDetector().detect(page, ["A"], originals=True)

    assert x == pytest.approx(400, abs=4)


def test_count_field_detector_starts_the_area_at_the_digit_boxes():
    page = blank_page()
    # A printed original count in a wider box, then four digit boxes and the label box.
    for x in (200, 400, 460, 520, 580, 640):
        page[800 : 800 + ROW, x : x + 3] = 0
    page[800 : 800 + ROW, 640:740] = 200
    lines = [("A", Line(820, 40, 760, None))]

    with mock.patch.object(CountFieldDetector, "read_lines", return_value=lines):
        ((_, (x, _, w, _)),) = CountFieldDetector().detect(page, ["A"], originals=True)
        ((_, (full_x, _, _, _)),) = CountFieldDetector().detect(page, ["A"])

    assert x == pytest.approx(400, abs=4)
    assert x + w == pytest.approx(640, abs=10)
    # Without printed originals, a wide written number is not cut at the boxes.
    assert full_x == pytest.approx(640 - CountFieldDetector.COUNT_WIDTH * WIDTH, abs=10)


def test_count_field_detector_inverts_a_black_box_cut_by_its_label_whole():
    part = blank_page()[:, :1736]
    part[800 : 800 + ROW, 600:720] = 20
    # The white label, too tall to leave more than a thin strip of box above and below it.
    part[815 : 800 + ROW - 15, 655:670] = 254

    inverted = CountFieldDetector.invert_black_boxes(part)

    # No black left above the label, where it would read into the description.
    assert inverted[805, 600:720].min() > 200
    assert inverted[800 + ROW // 2, 655:670].max() < 50


def test_count_field_detector_aligns_a_row_with_the_ruled_digit_boxes():
    page = blank_page()
    for y in (800, 800 + ROW):
        page[y : y + 3, 400:640] = 0

    # The description sits a quarter of a row low.
    assert CountFieldDetector.ruled_row(page, 400, 640, (821, 821 + ROW)) == (801, 801 + ROW)
    # Without ruled lines the row stays.
    assert CountFieldDetector.ruled_row(page, 1000, 1240, (821, 821 + ROW)) == (821, 821 + ROW)


def test_count_field_detector_keeps_a_row_with_a_dash_near_its_top():
    page = blank_page()
    page[800 + ROW : 800 + ROW + 3, 400:640] = 0
    # A dash for 0 a third of a row below the top line, which is too faint to find.
    page[828:832, 410:630] = 0

    assert CountFieldDetector.ruled_row(page, 400, 640, (821, 821 + ROW)) == (821, 821 + ROW)


def test_is_blank_ignores_the_ruled_digit_boxes():
    crop = np.full((ROW, 320), 254, np.uint8)
    crop[[0, -1], :] = 0
    crop[:, ::80] = 0

    assert is_blank(crop)

    write(crop, "17", 120, 65)
    assert not is_blank(crop)


def test_split_merged_rows_splits_a_row_twice_as_high():
    rows = [(0, 0, 50, 80), (0, 80, 50, 160), (0, 240, 50, 80), (0, 320, 50, 80)]

    assert split_merged_rows(rows) == [
        (0, 0, 50, 80),
        (0, 80, 50, 80),
        (0, 160, 50, 80),
        (0, 240, 50, 80),
        (0, 320, 50, 80),
    ]


def test_split_merged_rows_keeps_a_row_of_another_height():
    rows = [(0, 0, 50, 80), (0, 80, 50, 120), (0, 200, 50, 80)]

    assert split_merged_rows(rows) == rows


def test_columns():
    # Handwriting read into a description moves its start left; a box can be measured wrong either way.
    assert right_column([400, 560, 565, 570], 20) == 565
    assert main_column([400, 405, 410, 560], 20) == 405


def test_column_line_follows_the_slant_and_passes_over_wrong_positions():
    ys = [100, 200, 300, 400, 500, 600]
    # A slanted column, with one box measured a little wrong and one far off.
    xs = [440, 442, 462, 446, 448, 520]

    assert column_line(ys, xs, 25) == [440, 442, 444, 446, 448, 450]


def test_column_line_keeps_a_short_list_from_tilting():
    # Two of four boxes measured to the right, as on an admitted-voters page.
    line = column_line([100, 185, 270, 355], [440, 461, 440, 464], 25)

    assert line[-1] - line[0] <= 0.02 * 255 + 1


def test_column_line_takes_the_median_of_too_few_positions_for_a_slope():
    assert column_line([100, 300], [440, 446], 25) == [443, 443]


def test_gray_column_detector_numbers_rows_of_white_on_black():
    page = blank_page()
    left, top, width, rows = 900, 700, 100, 10
    page[top : top + rows * ROW, left : left + width] = 20
    for row in range(rows):
        write(page, str(row + 1), left + 20, top + row * ROW + 60, colour=255)

    _, tables = GrayColumnDetector().detect(page)

    assert [len(table) for table in tables] == [rows]


def test_gray_column_detector_ignores_a_piece_of_a_black_bar():
    page = blank_page()
    # A black "Totaal lijst" bar, cut up by its white text.
    page[3000:3090, 300:2200] = 20
    write(page, "Totaal lijst", 1600, 3060, colour=255)

    assert GrayColumnDetector().anchors(page) == []


def test_gray_column_detector_at_a_lower_level_separates_the_column_from_shaded_rows():
    page = blank_page()
    left, top, width, rows = 900, 700, 100, 12
    for row in range(0, rows, 2):
        page[top + row * ROW : top + (row + 1) * ROW, 200:1400] = 220
    page[top : top + rows * ROW, left : left + width] = 160
    for row in range(rows):
        write(page, str(row + 1), left + 20, top + row * ROW + 60)
    page[top : top + rows * ROW, left + width + 220 : left + width + 223] = 150

    _, tables = GrayColumnDetector(level=200).detect(page)

    assert [len(table) for table in tables] == [rows]
    assert tables[0][0][0] == left + width
