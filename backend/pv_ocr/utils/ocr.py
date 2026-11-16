"""The scale to render PV pages at, reading them with Tesseract, and matching the text OCR gives."""

import math
import re

import pytesseract
from PIL import Image

DPI = 300
# PVs are A4. A page beyond A3, in points with some slack for rounding, is a map or poster and is not read at all; a
# page in between renders at a lower resolution. An A0 page at full DPI took over 1Gi between the image and Tesseract.
MAX_PAGE_POINTS = (850, 1200)
MAX_PIXELS = round(210 / 25.4 * DPI) * round(297 / 25.4 * DPI)

# OCR mixes up digits and letters; TO_DIGIT turns the look-alikes back into digits.
OCR_DIGIT = "[0-9IlOoz]"
TO_DIGIT = str.maketrans("IlOoz", "11002")


def render_scale(width: float, height: float) -> float | None:
    """The scale to render a page of this size in points at, or None for a page beyond A3, which is not a PV."""
    if any(side > limit for side, limit in zip(sorted((width, height)), MAX_PAGE_POINTS)):
        return None
    return min(DPI / 72, math.sqrt(MAX_PIXELS / (width * height)))


def ocr(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang="nld", config="--psm 3")


def rotate_upright(image: Image.Image) -> Image.Image | None:
    """Rotate a scan upright using Tesseract's orientation detection, or None if it is upright or unknown."""
    try:
        angle = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)["rotate"]
    except pytesseract.TesseractError:
        return None
    # OSD gives the clockwise correction; PIL rotates anticlockwise.
    return image.rotate(-angle, expand=True) if angle else None


def letters_only(text: str) -> str:
    """Lowercase letters only, so OCR spacing, punctuation and hyphenation don't affect matching."""
    return re.sub(r"[^a-z]", "", text.lower())
