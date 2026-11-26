"""Find where the handwritten numbers are on a vote count page of a PV (Kiesraad models of November 2025).

One detector per page layout, each giving the areas a number is written in:

- GrayColumnDetector: candidate tables of name | number in a gray column | votes (N 10-1, Na 31-2 Bijlage 1). Ported
  from the gray column detector of kr-ocr-uitslagenportaal.
- BorderedTableDetector: candidate tables drawn in lines, the votes in the last four boxes (Na 14-1, Na 14-2 Bijlage 1).
- CountFieldDetector: the counts A–J, each written left of a label box and found by its printed description.

Pages are greyscale arrays, as `render_page` gives.
"""

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Iterator
from itertools import combinations
from typing import NamedTuple

import cv2
import numpy as np
import pytesseract
import regex

from pv_ocr.utils.ocr import OCR_DIGIT, TO_DIGIT, letters_only
from pv_ocr.utils.orientation import tesseract_image
from pv_ocr.utils.pv_toc import title_pattern

type Box = tuple[int, int, int, int]  # x, y, width, height

MAX_SKEW = 2.0  # degrees; more is a misreading of a short anchor, not a skewed scan
BLACK = 120  # below this a label box is black, above it gray
MAX_ROW = 0.045  # of the page height; candidate rows are about 0.025–0.03


def runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) of each run of True values, end exclusive."""
    d = np.diff(np.r_[False, flags, False].astype(np.int8))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def pairwise(values: list[int]) -> list[tuple[int, int]]:
    return list(zip(values[:-1], values[1:]))


def components(mask: np.ndarray) -> list[Box]:
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    return [(int(x), int(y), int(w), int(h)) for x, y, w, h, _ in stats[1:n]]


def kernel(width: float, height: float) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, int(width)), max(1, int(height))))


def rotate(gray: np.ndarray, degrees: float) -> np.ndarray:
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)


def fit_skew(ys: list[float], xs: list[float]) -> float:
    """Skew in degrees of a vertical edge through the points; positive leans right going down."""
    if len(ys) < 10:
        return 0.0
    ys, xs = np.array(ys, float), np.array(xs, float)
    slope, intercept = np.polyfit(ys, xs, 1)
    # Refit once without outliers, such as handwriting touching the edge.
    keep = np.abs(xs - (slope * ys + intercept)) < 3
    if keep.sum() >= 10:
        slope = np.polyfit(ys[keep], xs[keep], 1)[0]
    return float(np.degrees(np.arctan(slope)))


def split_merged_rows(table: list[Box]) -> list[Box]:
    """The rows, with one that is a whole number of rows high, where a line between them was missed, split up."""
    if len(table) < 3:
        return table
    pitch = float(np.median([h for _, _, _, h in table]))
    rows = []
    for x, y, w, h in table:
        n = round(h / pitch)
        if n >= 2 and abs(h - n * pitch) < 0.15 * pitch:
            rows += [(x, round(y + i * h / n), w, round(h / n)) for i in range(n)]
        else:
            rows.append((x, y, w, h))
    return rows


class VoteAreaDetector(ABC):
    """Finds the anchors of a layout, turns the page straight on them, and lays out the vote areas from them."""

    def detect(self, gray: np.ndarray) -> tuple[np.ndarray, list[list[Box]]]:
        """The deskewed page and its vote areas, as columns top to bottom, left to right."""
        anchors = self.anchors(gray)
        if not anchors:
            return gray, []
        # Even one degree of skew shifts a vote area by much of a digit over the height of a table.
        skew = self.skew(gray, max(anchors, key=lambda anchor: anchor[3]))
        if 0.05 < abs(skew) <= MAX_SKEW:
            gray = rotate(gray, -skew)
            anchors = self.anchors(gray)
        # A row taller than any candidate row means rows were missed from there on; the rows above it keep their
        # numbers, those below would get the wrong ones.
        tables = []
        for table in self.vote_areas(gray, anchors):
            # A filled header row above the candidates ("Stemmen" in white on black) is not one of them.
            while (
                table
                and np.median(gray[table[0][1] : table[0][1] + table[0][3], table[0][0] : table[0][0] + table[0][2]])
                < BLACK
            ):
                table = table[1:]
            table = split_merged_rows(table)
            tall = [i for i, (_, _, _, h) in enumerate(table) if h > MAX_ROW * gray.shape[0]]
            if table := table[: tall[0]] if tall else table:
                tables.append(table)
        return gray, tables

    @abstractmethod
    def anchors(self, gray: np.ndarray) -> list[Box]:
        """What the layout hangs on, left to right."""

    @abstractmethod
    def vote_areas(self, gray: np.ndarray, anchors: list[Box]) -> list[list[Box]]: ...

    def skew(self, gray: np.ndarray, band: Box) -> float:
        """Skew from the left edge of a solid band: the first dark run at least half the band wide on each line."""
        x, y, bw, bh = band
        mask = self.mask(gray)
        x0 = max(0, x - bw)
        ys, xs = [], []
        for yy in range(y + bh // 20, y + bh - bh // 20, 4):
            dark = np.flatnonzero(np.convolve(mask[yy, x0 : x + bw], np.ones(bw // 2), "valid") >= bw // 2 - 1)
            if len(dark):
                ys.append(yy)
                xs.append(x0 + dark[0])
        return fit_skew(ys, xs)

    def mask(self, gray: np.ndarray) -> np.ndarray:
        """Where the page is dark enough to be part of an anchor."""
        return cv2.medianBlur(gray, 5) < 200

    def solid_bands(self, gray: np.ndarray) -> list[Box]:
        """Areas of the mask that are solid over a rectangle lower than one row, so no text, lines or bars, and as wide
        as a number column or label box."""
        h, w = gray.shape
        solid = cv2.morphologyEx(self.mask(gray).astype(np.uint8), cv2.MORPH_OPEN, kernel(0.012 * w, 0.02 * h))
        # Narrower areas are heavy handwriting, wider ones are bars.
        return sorted(box for box in components(solid) if 0.028 * w < box[2] < 0.08 * w and box[3] >= 0.6 * box[2])

    @staticmethod
    def inner(gray: np.ndarray, band: Box) -> np.ndarray:
        """The band without its edges, which blur into the page."""
        x, y, bw, bh = band
        return gray[y : y + bh, x + bw // 6 : x + bw - bw // 6]


class GrayColumnDetector(VoteAreaDetector):
    """Candidate tables anchored on the gray column with the candidate numbers. The votes are written right of it, up
    to the table's thin right border; some gemeenten print row lines and digit boxes, others neither."""

    # The vote area is 2–4.5 times as wide as the number column, mostly about 2.2.
    VOTES_WIDTH = 2.2

    def __init__(self, level: int = 230):
        # Scans print the column anywhere from black to about 225. Where rows are shaded too, at about 220, only a
        # lower level tells them apart.
        self.level = level

    def mask(self, gray: np.ndarray) -> np.ndarray:
        # Bridge the thin light row separators in the column.
        mask = (cv2.medianBlur(gray, 5) < self.level).astype(np.uint8)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel(1, 0.006 * gray.shape[0])) > 0

    def anchors(self, gray: np.ndarray) -> list[Box]:
        """The number columns, gray or black, with the names to their left, which rules out the label boxes of the
        counts."""
        w = gray.shape[1]
        return [band for band in self.solid_bands(gray) if band[0] >= 0.25 * w and self.stands_free(gray, band)][:2]

    @staticmethod
    def stands_free(gray: np.ndarray, band: Box) -> bool:
        """Whether the band has paper on both sides, unlike a piece of a black bar cut out by its white text."""
        x, y, bw, bh = band
        sides = [gray[y : y + bh, max(0, x - 8) : x - 3], gray[y : y + bh, x + bw + 3 : x + bw + 8]]
        return all(side.size and np.median(side) > BLACK for side in sides)

    def vote_areas(self, gray: np.ndarray, anchors: list[Box]) -> list[list[Box]]:
        binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        w = gray.shape[1]
        tables = []
        prev_right = 0
        for band in anchors:
            x, top, bw, bh = band
            bottom, votes_left = top + bh, x + bw
            # The solid right border is darker than the dotted lines between digits.
            # Stay off the page margin, where a scan can have a dark edge.
            right = self.darkest_vertical_line(
                gray, top, bottom, votes_left + int(1.8 * bw), min(votes_left + int(4.5 * bw), int(0.97 * w))
            ) or votes_left + int(self.VOTES_WIDTH * bw)
            # The left border is the last solid vertical line left of the name column.
            search_from = max(prev_right + bw // 2, x - int(0.4 * w))
            left = self.last_solid_vertical_line(binary, top, bottom, search_from, x - bw // 2)
            if left is None or x - left < 3 * bw:
                left = max(search_from, x - int(0.28 * w))
            prev_right = right
            rows = self.rows_from_numbers(gray, band) or self.rows_from_lines(
                gray, top, bottom, left + bw // 4, x - bw // 4
            )
            tables.append([(votes_left, a, right - votes_left, b - a) for a, b in pairwise(rows)])
        return tables

    @staticmethod
    def darkest_vertical_line(gray: np.ndarray, y0: int, y1: int, x0: int, x1: int, max_median=225) -> int | None:
        """The x in [x0, x1) with the darkest median over [y0, y1), if dark enough. The table borders are thin gray
        lines that stand out in the median, not after binarisation."""
        x0, x1 = max(0, x0), min(gray.shape[1], x1)
        if x1 <= x0:
            return None
        profile = np.median(gray[y0:y1, x0:x1], axis=0)
        best = int(np.argmin(profile))
        return x0 + best if profile[best] <= max_median else None

    @staticmethod
    def last_solid_vertical_line(binary: np.ndarray, y0: int, y1: int, x0: int, x1: int, min_fill=0.85) -> int | None:
        x0, x1 = max(0, x0), min(binary.shape[1], x1)
        if x1 <= x0:
            return None
        hits = np.flatnonzero((binary[y0:y1, x0:x1] > 0).mean(axis=0) >= min_fill)
        return x0 + int(hits[-1]) if len(hits) else None

    # How much a printed number differs from the column: from faint gray on light gray to white on black.
    NUMBER_CONTRASTS = (30, 40, 60, 80)

    def rows_from_numbers(self, gray: np.ndarray, band: Box) -> list[int] | None:
        """Row boundaries halfway between the candidate numbers printed in the column, which works with or without
        row lines. The numbers are evenly spaced; None when they are not at any contrast, such as with handwriting in
        the band."""
        # Blurring takes out the speckle of a halftone column.
        inner = cv2.medianBlur(self.inner(gray, band), 3).astype(int)
        deviation = np.abs(inner - np.median(inner, axis=1, keepdims=True))
        min_height = max(3, int(0.004 * gray.shape[0]))
        best: list[float] = []
        for contrast in self.NUMBER_CONTRASTS:
            ink = (deviation > contrast).sum(axis=1) > 1
            centres = [band[1] + (a + b) / 2 for a, b in runs(ink) if b - a >= min_height]
            gaps = np.diff(centres)
            if len(centres) > len(best) and (not len(gaps) or gaps.max() <= 1.5 * gaps.min()):
                best = centres
        if not best:
            return None
        return [band[1]] + [round((a + b) / 2) for a, b in pairwise(best)] + [band[1] + band[3]]

    @staticmethod
    def rows_from_lines(gray: np.ndarray, top: int, bottom: int, x0: int, x1: int) -> list[int]:
        """Row boundaries from the light row separator lines across the name column."""
        profile = np.median(gray[top:bottom, x0:x1], axis=1).astype(float)
        d = 4
        score = np.zeros_like(profile)
        score[d:-d] = (profile[: -2 * d] + profile[2 * d :]) / 2 - profile[d:-d]
        candidates = [y for a, b in runs(score > 8) if top + 8 < (y := top + (a + b) // 2) < bottom - 8]
        if not candidates:
            return [top, bottom]

        height = bottom - top
        lines = np.array(candidates)
        # An absolute tolerance: one relative to the pitch would let coarse splits always match.
        tolerance = 0.004 * gray.shape[0]

        def match_ratio(n: int) -> float:
            inner = top + (height / n) * np.arange(1, n)
            return float((np.abs(inner[:, None] - lines[None, :]).min(axis=1) < tolerance).mean())

        # A divisor of the row count matches everywhere too, a multiple only half: take the largest n that matches.
        ratios = {n: match_ratio(n) for n in range(2, max(2, int(height / (0.012 * gray.shape[0]))) + 1)}
        best = max(ratios.values())
        n = max(k for k, ratio in ratios.items() if ratio >= min(0.9, best - 0.05))
        pitch = height / n

        rows = [top]
        for i in range(1, n):
            y = round(top + i * pitch)
            near = int(lines[np.abs(lines - y).argmin()])
            rows.append(near if abs(near - y) < 0.25 * pitch else y)
        return rows + [bottom]


class BorderedTableDetector(VoteAreaDetector):
    """Candidate tables drawn in lines, ending in four digit boxes. Those are anchored on their five vertical lines,
    the rows on the horizontal lines between them. Na 14-2 Bijlage 1 prints the original count before them, in a gray
    column or in boxes of its own; only the last boxes are handwritten."""

    DIGIT_BOXES = 4
    # Digit boxes are 1.2–6% of the page wide, and within 30% of each other.
    DIGIT_WIDTH = (0.012, 0.06)
    SIMILAR_WIDTH = 0.3

    def vertical_lines(self, gray: np.ndarray) -> list[Box]:
        """Vertical lines taller than one row, left to right. Widening them first keeps a thin line that leans a
        little."""
        h, w = gray.shape
        mask = cv2.dilate((gray < 200).astype(np.uint8), kernel(3, 1))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel(1, 0.006 * h))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel(1, 0.04 * h))
        # A shaded column, such as one with the candidate numbers, ends in a line on its right.
        boxes = [box if box[2] < 0.02 * w else (box[0] + box[2] - 3, box[1], 3, box[3]) for box in components(mask)]
        # A scanned line can break up into pieces, less than a row apart at the same x. A subtotal row is further off.
        lines: list[Box] = []
        for x, y, lw, lh in sorted((box for box in boxes if box[2] < 0.02 * w), key=lambda box: (box[1], box[0])):
            for i, (px, py, pw, ph) in enumerate(lines):
                if abs(x - px) <= 0.004 * w and max(py, y) - min(py + ph, y + lh) <= 0.03 * h:
                    top, bottom = min(py, y), max(py + ph, y + lh)
                    lines[i] = (min(px, x), top, max(px + pw, x + lw) - min(px, x), bottom - top)
                    break
            else:
                lines.append((x, y, lw, lh))
        return sorted(lines)

    def anchors(self, gray: np.ndarray) -> list[Box]:
        """The digit boxes of each table: four boxes as wide as the last, between lines of about the same height,
        found from the right. Shorter lines in between, of a subtotal row or handwriting, and those of boxes found
        already are passed over; a column line of another width ends the boxes."""
        w = gray.shape[1]
        low, high = self.DIGIT_WIDTH[0] * w, self.DIGIT_WIDTH[1] * w

        def same_height(a: Box, b: Box) -> bool:
            # Handwriting can break a line, here or further than a subtotal row; its pieces count together.
            pieces = [line for line in lines if abs(line[0] - b[0]) <= 0.004 * w]
            overlap = sum(max(0, min(a[1] + a[3], p[1] + p[3]) - max(a[1], p[1])) for p in pieces)
            return overlap >= 0.6 * max(a[3], b[3])

        lines = self.vertical_lines(gray)
        anchors, used = [], set()
        for i in reversed(range(len(lines))):
            if i in used:
                continue
            run = [i]
            for j in reversed(range(i)):
                gap = lines[run[-1]][0] - lines[j][0]
                if gap > high:
                    break
                last_gap = lines[run[0]][0] - lines[run[1]][0] if len(run) > 1 else gap
                if gap >= low and j not in used and same_height(lines[i], lines[j]):
                    if abs(gap - last_gap) > self.SIMILAR_WIDTH * last_gap:
                        break
                    run.append(j)
                    if len(run) > self.DIGIT_BOXES:
                        break
            if len(run) > self.DIGIT_BOXES:
                used.update(run)
                boxes = [lines[k] for k in reversed(run)]
                left, right = boxes[0][0], boxes[-1][0] + boxes[-1][2]
                # A line can fade out before the end of the table.
                top = min(box[1] for box in boxes)
                bottom = max(box[1] + box[3] for box in boxes)
                anchors.append((left, top, right - left, bottom - top))
        anchors.sort()

        def printed(a: Box, b: Box) -> bool:
            # Na 14-2 Bijlage 1 can print the original count in boxes right before the handwritten ones, which can be
            # wider.
            box = max(a[2], b[2]) / self.DIGIT_BOXES
            overlap_y = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
            return -box < b[0] - (a[0] + a[2]) < box and overlap_y > a[3] / 2

        def below(a: Box, b: Box) -> bool:
            # The digit boxes of a subtotal, or the same boxes found again, start below those of their table.
            return b[1] < a[1] and b[0] < a[0] + a[2] and a[0] < b[0] + b[2]

        anchors = [a for a in anchors if not any(printed(a, b) for b in anchors)]
        return [a for a in anchors if not any(below(a, b) for b in anchors)]

    def skew(self, gray: np.ndarray, area: Box) -> float:
        """Skew from the rightmost vertical line of the digit boxes; the leftmost can be the edge of a shaded column,
        which `vertical_lines` gives as upright."""
        x, y, w, h = area
        # A subtotal row can end in a line at the same x.
        line = max((line for line in self.vertical_lines(gray) if line[0] + line[2] == x + w), key=lambda line: line[3])
        lx, ly, lw, lh = line
        ys, xs = [], []
        for yy in range(ly, ly + lh, 4):
            dark = np.flatnonzero(gray[yy, lx : lx + lw] < 180)
            if len(dark):
                ys.append(yy)
                xs.append(lx + dark.mean())
        return fit_skew(ys, xs)

    def vote_areas(self, gray: np.ndarray, anchors: list[Box]) -> list[list[Box]]:
        tables = []
        for x, y, w, h in anchors:
            # Horizontal lines run across most of the boxes; their centres bound the rows.
            dark = (gray[y : y + h, x : x + w] < 180).mean(axis=1) >= 0.6
            lines = [y + (a + b) // 2 for a, b in runs(dark)]
            if not lines or lines[0] - y > 0.01 * gray.shape[0]:
                lines.insert(0, y)
            rows = [(a, b) for a, b in pairwise(lines) if b - a >= 0.012 * gray.shape[0]]
            if len(rows) > 1:
                pitch = np.median([b - a for a, b in rows])
                # A dash written for 0 across the boxes splits its row in two.
                merged = []
                for a, b in pairwise(lines):
                    if merged and abs(b - merged[-1][0] - pitch) < 0.15 * pitch:
                        merged[-1] = (merged[-1][0], b)
                    else:
                        merged.append((a, b))
                # The lines can run up through a lower header row ("Stemmen").
                rows = [(a, b) for a, b in merged if b - a >= 0.7 * pitch]
            if not rows:
                rows = self.rows_from_number_column(gray, x)
            if rows:
                tables.append([(x, a, w, b - a) for a, b in rows])
        return tables

    @staticmethod
    def rows_from_number_column(gray: np.ndarray, x: int) -> list[tuple[int, int]]:
        """Rows from the candidate numbers in a gray column right before the boxes, where shading marks the rows
        instead of lines."""
        column = GrayColumnDetector()
        for band in column.anchors(gray):
            if abs(band[0] + band[2] - x) < 0.02 * gray.shape[1]:
                return pairwise(column.rows_from_numbers(gray, band) or [])
        return []


class Line(NamedTuple):
    """Where Tesseract read the description of a count, and the label before it."""

    top: int
    height: int
    description_left: int
    label: tuple[int, int] | None  # left and width


# The description after each label box, which names the count. E.<n> is "Totaal lijst <n>"; I and J share theirs
# but for méér or minder, which OCR cannot tell apart reliably by spelling alone.
DESCRIPTIONS = [
    ("A", "stempassen"),
    ("B", "volmachtbewijzen"),
    ("C", "kiezerspassen"),
    ("D", "totaaltoegelatenkiezers"),
    ("E", "totaalstemmenopkandidaten"),
    ("F", "blancostemmen"),
    ("G", "ongeldigestemmen"),
    ("H", "totaaluitgebrachtestemmen"),
    ("E.", "totaallijst"),
]
DESCRIPTION_KEYS = [(field, title_pattern(key)) for field, key in DESCRIPTIONS]
# "Totaal" is bold against a black box, and read as up to five other letters ("ros", "Frea"). The rest of the
# description is particular enough without it: the "(A+B)" and "(E+F+G)" endings keep out running text ("het aantal
# toegelaten kiezers") and the heading "Uitgebrachte stemmen"; "stemmen op kandidaten" is found nowhere else.
TOTAL_KEYS = [
    ("D", regex.compile(r"[a-z]{0,5}?(?:toegelatenkiezers){e<=2}ab")),
    ("E", regex.compile(r"[a-z]{0,5}?(?:stemmenopkandidaten){e<=2}")),
    ("H", regex.compile(r"[a-z]{0,5}?(?:uitgebrachtestemmen){e<=2}efg")),
]
DIFFERENCE_RE = regex.compile(r"(?:aantal){e<=1}(\w{1,8}?)(?:getelde){e<=1}")
PUNCTUATION = "_-–—‚,.'\"(|"
# A label as OCR reads it: "E.1", "E1", "(D", "H".
LABEL_RE = re.compile(r"^\W?(?:[A-J]|E\.?\d{1,2})\W?$")
LIST_NUMBER_RE = re.compile(rf"[lLtI]ijs[tl]\s*({OCR_DIGIT}{{1,2}})")


class CountFieldDetector:
    """The counts A–J: each is written left of a label box, followed by its description ("Blanco stemmen", "Totaal
    lijst 3"). Templates differ in how they draw the boxes, but not in the descriptions, so Tesseract reads those to
    find and name the fields."""

    # Each segmentation mode misses lines the other finds; together they find about 95% of the counts.
    PAGE_SEGMENTATION_MODES = (3, 12)
    # The number is written in up to 12% of the page width left of its box.
    COUNT_WIDTH = 0.12
    # The width of a label box, with its margins, where no label on the page is read.
    LABEL_WIDTH = 0.05

    def detect(self, gray: np.ndarray, fields: list[str], originals: bool = False) -> list[tuple[str, Box]]:
        """The area of each of the fields found, in the order of `fields`; a field read out of order is left out.
        With `originals`, a printed original count before each field is left out of its area."""
        h, w = gray.shape
        part = self.invert_black_boxes(gray[:, : int(0.7 * w)].copy())
        candidates = [
            (field, line)
            for mode in self.PAGE_SEGMENTATION_MODES
            for field, line in self.read_lines(part, mode)
            if field in fields
        ]
        # Both modes mostly read the same line; a stray word merged in only moves its start left.
        candidates.sort(key=lambda c: (fields.index(c[0]), c[1].top))
        unique = []
        for field, line in candidates:
            if unique and unique[-1][0] == field and line.top - unique[-1][1].top < 0.01 * h:
                if line.description_left > unique[-1][1].description_left:
                    unique[-1] = (field, line)
            else:
                unique.append((field, line))
        found = in_order(unique, fields)
        if not found:
            return []
        # The descriptions start in one column. Handwriting read into the first word ("lTotaal") moves a start left.
        column = right_column([line.description_left for _, line in found], 0.02 * w)
        found = [(field, line._replace(description_left=max(line.description_left, column))) for field, line in found]

        centres = [line.top + line.height / 2 for _, line in found]
        gaps = [b - a for a, b in pairwise(centres)]
        half = float(np.clip(np.median(gaps) / 2, 0.010 * h, 0.016 * h)) if gaps else 0.0125 * h
        rows = [(max(0, round(c - half)), min(h, round(c + half))) for c in centres]
        rights = [self.label_box_left(gray, row, line) for (_, line), row in zip(found, rows)]
        # Where a box is not found, it is as far from its description as the others.
        spans = [line.description_left - right for (_, line), right in zip(found, rights) if right is not None]
        span = np.median(spans) if spans else self.LABEL_WIDTH * w
        rights = [
            right if right is not None else round(line.description_left - span)
            for (_, line), right in zip(found, rights)
        ]
        # The label boxes are in one column too, slanting with the scan; a box can be measured wrong either way, so each
        # area ends at the line through most of them.
        areas = []
        for (field, line), row, right in zip(found, rows, column_line(centres, rights, 0.01 * w)):
            top, bottom = self.ruled_row(gray, right - round(self.COUNT_WIDTH * w), right, row)
            bounds = (max(0, right - round(self.COUNT_WIDTH * w)), top, right, bottom)
            left = bounds[0]
            if originals:
                # Handwriting in the first box can pass for gray fill, so the digit boxes go first.
                left = self.digit_boxes_start(gray, bounds)
                if left == bounds[0]:
                    left = self.after_gray_fill(gray, bounds)
            if right - left > 0.02 * w:
                areas.append((field, (left, top, right - left, bottom - top)))
        return areas

    @staticmethod
    def ruled_row(gray: np.ndarray, x0: int, x1: int, row: tuple[int, int]) -> tuple[int, int]:
        """The row centred between the ruled lines of its digit boxes nearest its top and bottom, where both are within
        a third of a row; a description can be printed off the middle of its row. Lines closer together than most of
        a row include a dash written for 0, and digits can stick out of their boxes, so the row keeps its height."""
        top, bottom = row
        h = bottom - top
        y0, y1 = max(0, top - h // 2), min(gray.shape[0], bottom + h // 2)
        dark = (gray[y0:y1, max(0, x0) : x1] < 160).mean(axis=1) >= 0.6
        lines = [y0 + (a + b) // 2 for a, b in runs(dark)]

        def nearest(y: int) -> int | None:
            return min((line for line in lines if abs(line - y) < h / 3), key=lambda line: abs(line - y), default=None)

        ruled_top, ruled_bottom = nearest(top), nearest(bottom)
        if ruled_top is None or ruled_bottom is None or ruled_bottom - ruled_top < 0.8 * h:
            return row
        shift = (ruled_top + ruled_bottom) // 2 - (top + bottom) // 2
        return top + shift, bottom + shift

    @staticmethod
    def label_box_left(gray: np.ndarray, row: tuple[int, int], line: Line) -> int | None:
        """The left edge of the label box before a description: of a black or gray box, or else mirrored around the
        label in it. None when neither is found. The box is the run nearest the description."""
        w = gray.shape[1]
        top, bottom = row
        quarter = (bottom - top) // 4
        x0, x1 = max(0, line.description_left - round(0.1 * w)), line.description_left

        def nearest(dark: np.ndarray) -> int | None:
            # A wide white label ("I") can cut a box in two; a grid line or pen stroke next to it is too thin to join.
            merged: list[tuple[int, int]] = []
            for a, b in runs(dark):
                if merged and a - merged[-1][1] < 0.005 * w and min(b - a, merged[-1][1] - merged[-1][0]) >= 0.01 * w:
                    merged[-1] = (merged[-1][0], b)
                else:
                    merged.append((a, b))
            for a, b in reversed(merged):
                if x1 - (x0 + b) < 0.05 * w and 0.015 * w < b - a < 0.09 * w:
                    return x0 + a
            return None

        # A black box first, as its white label cuts its height in two: the digit grid next to it is as dark as a
        # gray box.
        profile = np.median(cv2.blur(gray[top + quarter : bottom - quarter, x0:x1], (15, 15)), axis=0)
        if (left := nearest(profile < BLACK)) is not None:
            return left
        # A gray box is dark over almost all of its height, unlike handwriting touching it.
        band = cv2.medianBlur(gray[top + quarter : bottom - quarter, x0:x1], 5)
        if (left := nearest((band < np.median(gray) - 4).mean(axis=0) > 0.8)) is not None:
            return left
        if line.label:
            return min(2 * line.label[0] + line.label[1] - line.description_left, line.label[0])
        return None

    @staticmethod
    def invert_black_boxes(part: np.ndarray) -> np.ndarray:
        """Turn the white labels on black boxes dark on white, which Tesseract reads."""
        h, w = part.shape
        black = cv2.morphologyEx(
            (cv2.medianBlur(part, 5) < 100).astype(np.uint8), cv2.MORPH_OPEN, kernel(0.012 * w / 0.7, 0.012 * h)
        )
        # The label can cut its box in two; inverted apart, the black between them reads into the description.
        black = cv2.morphologyEx(black, cv2.MORPH_CLOSE, kernel(0.012 * w / 0.7, 1))
        for x, y, bw, bh in components(black):
            if bw < 0.08 * w / 0.7:
                part[y : y + bh, x : x + bw] = 255 - part[y : y + bh, x : x + bw]
        return part

    @staticmethod
    def read_lines(part: np.ndarray, mode: int) -> Iterator[tuple[str, Line]]:
        data = pytesseract.image_to_data(
            tesseract_image(part), lang="nld", config=f"--psm {mode}", output_type=pytesseract.Output.DICT
        )
        lines = defaultdict(list)
        for i, text in enumerate(data["text"]):
            if text.strip():
                lines[(data["block_num"][i], data["par_num"][i], data["line_num"][i])].append(i)
        for words in lines.values():
            texts = [data["text"][i] for i in words]
            match = None
            for k, i in enumerate(words):
                # A description follows a label ("E‚3 {Totaal lijst 3"), or starts the line; in running text it
                # follows a lowercase word ("aantal geldige stempassen en volmachtbewijzen"), where a misread label
                # is capitalised ("ES Totaal lijst 5"). The label and handwriting read as words ("W, 5", "Ò"), or
                # glued to it ("|__\Aantal"), can match along with it, so the rightmost start that matches wins.
                previous = texts[k - 1].strip(PUNCTUATION) if k else ""
                if (
                    not re.sub(r"^[\W_]+", "", texts[k])[:1].isalpha()
                    or len(previous) > 4
                    or len(previous) > 1
                    and previous.isalpha()
                    and previous.islower()
                ):
                    continue
                if field := description_field(texts[k : k + 6]):
                    labelled = k and LABEL_RE.match(texts[k - 1])
                    label = (data["left"][words[k - 1]], data["width"][words[k - 1]]) if labelled else None
                    match = field, Line(data["top"][i], data["height"][i], data["left"][i], label)
            if match:
                yield match

    @staticmethod
    def after_gray_fill(gray: np.ndarray, bounds: tuple[int, int, int, int]) -> int:
        """Where the area within bounds (x0, y0, x1, y1) starts: past the last gray fill in its left half, which holds
        a printed original count (Na 14-2 Bijlage 1)."""
        x0, y0, x1, y1 = bounds
        paper = int(np.median(gray)) - 4
        profile = np.median(cv2.blur(gray[y0:y1, x0:x1], (15, 15)), axis=0)
        fills = [b for a, b in runs((profile >= BLACK) & (profile < paper)) if b - a >= 0.01 * gray.shape[1]]
        fills = [b for b in fills if b < (x1 - x0) / 2]
        return x0 + fills[-1] if fills else x0

    @staticmethod
    def digit_boxes_start(gray: np.ndarray, bounds: tuple[int, int, int, int]) -> int:
        """Where the area within bounds (x0, y0, x1, y1) starts: at the first of the digit boxes ending it, if it has
        three or more of the same width; a wider box before them holds a printed original count. A stroke written in a
        box can pass for a line, so each step goes to the line closest to one box further."""
        x0, y0, x1, y1 = bounds
        w = gray.shape[1]
        quarter = (y1 - y0) // 4
        dark = (gray[y0 + quarter : y1 - quarter, x0:x1] < 160).mean(axis=0) >= 0.8
        lines = [x0 + (a + b) // 2 for a, b in runs(dark)]

        def boxes_of(width: int) -> tuple[int, int]:
            start, boxes = len(lines) - 1, 0
            while fits := [i for i in range(start) if abs(lines[start] - lines[i] - width) <= 0.3 * width]:
                start = min(fits, key=lambda i: abs(lines[start] - lines[i] - width))
                boxes += 1
            return boxes, start

        widths = [lines[-1] - line for line in lines[:-1] if 0.012 * w <= lines[-1] - line <= 0.06 * w]
        boxes, start = max((boxes_of(width) for width in widths), key=lambda result: result[0], default=(0, 0))
        return lines[start] if boxes >= 3 else x0


def description_field(words: list[str]) -> str | None:
    """The count whose description the words start with, if any."""
    text = letters_only("".join(words))
    if match := DIFFERENCE_RE.match(text):
        return "J" if regex.search(r"(?:inder){e<=1}", match.group(1)) else "I"
    for field, pattern in DESCRIPTION_KEYS:
        if pattern.match(text):
            if field != "E.":
                return field
            number = LIST_NUMBER_RE.search(" ".join(words[:4]))
            return f"E.{int(number.group(1).translate(TO_DIGIT))}" if number else None
    return next((field for field, pattern in TOTAL_KEYS if pattern.match(text)), None)


def right_column(xs: list[int], tolerance: float) -> int:
    """Where the rightmost column is: the median of the positions within `tolerance` of the rightmost one."""
    right = max(xs)
    return int(np.median([x for x in xs if right - x < tolerance]))


def main_column(xs: list[int], tolerance: float) -> int:
    """Where most positions are, within `tolerance`; the rightmost such column on a tie."""
    clusters = [[x for x in xs if abs(x - start) < tolerance] for start in xs]
    return int(np.median(max(clusters, key=lambda c: (len(c), np.median(c)))))


def column_line(ys: list[float], xs: list[int], tolerance: float) -> list[int]:
    """Where a column is at each y: on the line through the positions within `tolerance` of the main column, with the
    median slope between them, so that a few positions measured wrong don't tilt it."""
    column = main_column(xs, tolerance)
    points = [(y, x) for y, x in zip(ys, xs) if abs(x - column) < tolerance]
    slopes = [(x2 - x1) / (y2 - y1) for (y1, x1), (y2, x2) in combinations(points, 2) if y2 != y1]
    # A scan is skewed by a degree at most; a steeper slope comes from a short list with boxes measured wrong.
    slope = float(np.clip(np.median(slopes), -0.02, 0.02)) if len(points) >= 3 else 0.0
    offset = float(np.median([x - slope * y for y, x in points]))
    return [round(offset + slope * y) for y in ys]


def in_order(candidates: list[tuple[str, Line]], fields: list[str]) -> list[tuple[str, Line]]:
    """The most fields among the candidates that come both in the order of `fields` and top to bottom. A misread
    field, such as E.8 for E.6, or a description in running text breaks the order and is left out."""
    best: list[list[int]] = []
    for i, (field, line) in enumerate(candidates):
        runs_before = [
            run
            for j, run in enumerate(best[:i])
            if fields.index(candidates[run[-1]][0]) < fields.index(field) and candidates[run[-1]][1].top < line.top
        ]
        best.append(max(runs_before, key=len, default=[]) + [i])
    return [candidates[i] for i in max(best, key=len, default=[])]


def is_blank(crop: np.ndarray) -> bool:
    """Whether a vote area holds no writing: hardly any ink once the ruled lines are taken out. Ruled lines are thin,
    possibly dotted, and cross the whole area, as the area is cut from a table; a written 1 never quite does."""
    h, w = crop.shape
    ink = (crop < 190).astype(np.uint8)
    # Outside the crop is paper: OpenCV otherwise erodes as if ink went on, so a 1 touching the edge would pass.
    paper = {"borderType": cv2.BORDER_CONSTANT, "borderValue": 0}
    across = cv2.morphologyEx(
        cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel(9, 1)), cv2.MORPH_OPEN, kernel(0.6 * w, 1), **paper
    )
    down = cv2.morphologyEx(
        cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel(1, 9)), cv2.MORPH_OPEN, kernel(1, 0.97 * h), **paper
    )
    lines = np.zeros_like(ink)
    for x, y, bw, bh in components(across):
        if bh <= 12:
            lines[y : y + bh, x : x + bw] = 1
    for x, y, bw, bh in components(down):
        if bw <= 12:
            lines[y : y + bh, x : x + bw] = 1
    ink[cv2.dilate(lines, kernel(3, 3)) > 0] = 0
    # Leave out specks, and the edges, which cut through lines and the shading of a column next to the area. The last
    # digit is written against the right edge, so less is left out there.
    my, ml, mr = max(4, round(0.06 * h)), max(4, round(0.06 * w)), max(4, round(0.03 * w))
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel(2, 2))[my:-my, ml:-mr]
    return ink.mean() < 0.004
