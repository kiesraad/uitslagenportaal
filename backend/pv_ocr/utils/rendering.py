"""Sizes for rendering PV pages to images for OCR."""

import math

DPI = 300
# PVs are A4. A page beyond A3, in points with some slack for rounding, is a map or poster and is not read at all; a
# page in between renders at a lower resolution. An A0 page at full DPI took over 1Gi between the image and Tesseract.
MAX_PAGE_POINTS = (850, 1200)
MAX_PIXELS = round(210 / 25.4 * DPI) * round(297 / 25.4 * DPI)


def render_scale(width: float, height: float) -> float | None:
    """The scale to render a page of this size in points at, or None for a page beyond A3, which is not a PV."""
    if any(side > limit for side, limit in zip(sorted((width, height)), MAX_PAGE_POINTS)):
        return None
    return min(DPI / 72, math.sqrt(MAX_PIXELS / (width * height)))
