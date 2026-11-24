"""Turning a page upright with Tesseract's orientation detection. Pages are greyscale arrays, as `render_page` gives."""

import cv2
import numpy as np
import pytesseract
from PIL import Image

# OSD gives the clockwise correction.
TURNS = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def tesseract_image(gray: np.ndarray) -> Image.Image:
    """The page for pytesseract to pass on uncompressed, as a PGM, which Pillow writes under "PPM". Like a PNG it holds
    no dpi, so Tesseract estimates the resolution as before."""
    image = Image.fromarray(gray)
    image.format = "PPM"
    return image


def osd_rotation(gray: np.ndarray) -> int:
    try:
        osd = pytesseract.image_to_osd(tesseract_image(gray), output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractError:
        return 0
    return osd["rotate"] if osd["orientation_conf"] > 1 else 0


def rotation(gray: np.ndarray) -> int:
    """The clockwise turn that puts the page upright: 0, 90, 180 or 270. A table scanned upside down looks the same to
    the detectors, but with its rows reversed. Half the resolution is twice as fast, but can take an upright page for
    one upside down, so a turn is confirmed at full resolution."""
    if osd_rotation(cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)) not in TURNS:
        return 0
    full = osd_rotation(gray)
    return full if full in TURNS else 0


def turn(gray: np.ndarray, degrees: int) -> np.ndarray:
    """The page turned clockwise by `degrees`, as `rotation()` gives."""
    return cv2.rotate(gray, TURNS[degrees]) if degrees in TURNS else gray


def upright(gray: np.ndarray) -> np.ndarray:
    return turn(gray, rotation(gray))
