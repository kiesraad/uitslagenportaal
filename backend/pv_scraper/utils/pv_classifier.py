"""POC: classify processen-verbaal by model and, where possible, region, using Tesseract on the first two pages.

A model counts as identified when its code and its title are both on the page, or its title alone. The classify_pvs
management command runs it on a folder of PDFs.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Self

import pypdfium2 as pdfium
import pytesseract
import regex
from PIL import Image

DPI = 300
# OCR of the top 40% first is fastest overall, although OSV forms, whose titles sit lower, then need a full page.
CROP_FRACTION = 0.4

# Known models; a code outside this list is taken to be misread. A bijlage is an attachment to a PV, not the PV
# itself, so it is a model of its own: "<code> Bijlage <n>".
MODELS = {
    "N 10-1": "stembureau, decentrale stemopneming",
    "N 10-2": "stembureau, centrale stemopneming",
    "Na 14-1": "corrigendum stembureau, herteld door gemeentelijk stembureau",
    "Na 14-2": "corrigendum gemeentelijk stembureau",
    "Na 14-2 Bijlage 1": "corrigendum gemeentelijk stembureau, verslagen van hertelde stembureaus",
    "Na 31-1": "gemeentelijk stembureau, decentrale stemopneming",
    "Na 31-2": "gemeentelijk stembureau, centrale stemopneming",
    "Na 31-2 Bijlage 1": "gemeentelijk stembureau, verslagen van tellingen van stembureaus",
    "Na 31-2 Bijlage 2": "gemeentelijk stembureau, bezwaren van aanwezigen op stembureaus",
    "O 7": "hoofdstembureau",
    "P 1f-1": "corrigendum hoofdstembureau",
    "P 2a": "nieuwe zitting gemeentelijk stembureau, gecorrigeerde telresultaten",
    "P 22-1": "centraal stembureau, uitslag TK, EP en PS met meer dan één kieskring",
    "P 22-2": "centraal stembureau, uitslag en zetelverdeling",
    "I 1": "centraal stembureau, onderzoek kandidatenlijsten",
    "I 4": "centraal stembureau, kandidatenlijsten en nummering",
}

# Texts that appear on one model only, from the forms the Kiesraad published on 27 November 2025 as OSV fills them in;
# the I, O 7, P 1f-1 and P 22-1 forms have no newer version. Forms of earlier elections word and number things
# differently, so they are left unidentified. OSV headers such as "Verslag en telresultaten per lijst en kandidaat"
# and "Details van het stembureau" are shared by several models.
TITLES = [
    ("hoeveel stemmen elke lijst en elke kandidaat hebben gekregen", "N 10-1"),
    ("hoeveel stemmen elke lijst heeft gekregen", "N 10-2"),
    ("Corrigendum van een proces-verbaal van een stembureau", "Na 14-1"),
    ("Verslag van telling van een door het gemeentelijk stembureau herteld stembureau", "Na 14-1"),
    ("Corrigendum van een gemeentelijk stembureau", "Na 14-2"),
    ("Verslagen van tellingen van stembureaus die zijn herteld door het gemeentelijk stembureau", "Na 14-2 Bijlage 1"),
    ("hoeveel stemmen elke lijst en elke kandidaat kreeg", "Na 31-1"),
    ("Het gemeentelijk stembureau telt de stemmen per kandidaat", "Na 31-2"),
    ("Bijlage 1 - verslag telling stembureau", "Na 31-2 Bijlage 1"),
    ("Verslagen van tellingen van stembureaus", "Na 31-2 Bijlage 1"),
    ("Bezwaren van aanwezigen op stembureaus", "Na 31-2 Bijlage 2"),
    ("Proces-verbaal van een hoofdstembureau", "O 7"),
    ("Corrigendum bij het proces-verbaal van een hoofdstembureau", "P 1f-1"),
    ("Verslag en gecorrigeerde telresultaten", "P 2a"),
    ("Proces-verbaal van het centraal stembureau met de uitslag van de verkiezing", "P 22-1"),
    ("Verslag, uitslag en zetelverdeling", "P 22-2"),
    ("Proces-verbaal van het onderzoek naar de kandidatenlijsten", "I 1"),
    ("Proces-verbaal over geldigheid en nummering kandidatenlijsten", "I 4"),
]


def letters_only(text: str) -> str:
    """Lowercase letters only, so OCR spacing, punctuation and hyphenation don't affect matching."""
    return re.sub(r"[^a-z]", "", text.lower())


# Up to two misread letters still match a title ("sternbureaus", "têllingen").
TITLE_ERRORS = 2
TITLE_KEYS = [
    (key, regex.compile(f"(?e)(?:{key}){{e<={TITLE_ERRORS}}}"), model)
    for key, model in ((letters_only(title), model) for title, model in TITLES)
]


def pv_code(model: str) -> str:
    """The code printed on the page: a bijlage carries the code of the PV it belongs to."""
    return model.split(" Bijlage")[0]


PV_CODES = {pv_code(model) for model in MODELS}

# How a model was decided, best first. Only the first two count as identified.
BASES = ["code+title", "title", "code", "conflict", "unknown", "none"]

# OCR mixes up digits and letters ("Model N I0-z", "Model [ 1", "Modei"), drops spaces ("ModelNa31-2") and sometimes
# the letters ("Model 31-1"). The letter I is only taken from a look-alike followed by a space, so "Model 1 1" is I 1.
OCR_DIGIT = "[0-9IlOoz]"
I_LOOKALIKE = "|[1l"
MODEL_RE = re.compile(
    rf"(?i:\bmode[li1])\s*(?:([A-Z][a-z]?|[{re.escape(I_LOOKALIKE)}](?=\s))\s*-?)?"
    rf"\s*({OCR_DIGIT}{{1,2}})([a-z](?![a-z]))?(?:\s*[-–—~.]\s*({OCR_DIGIT}))?"
)
TO_DIGIT = str.maketrans("IlOoz", "11002")

GEMEENTE_RE = re.compile(r"(?i:gemeente)[:\s]*(\d{3,4})\b")
STEMBUREAU_RE = re.compile(r"(?i:stembureau(?:nummer)?|nummer\s*stembureau)[:\s]*(?:nr\.?)?\s*(\d{1,4})\b")
KIESKRING_RE = re.compile(r"(?i:kieskring)[:\s]*(\d{1,2})\b")

# The election is named with its year a few words later: "de leden van de gemeenteraad van Brummen op 18 maart
# 2026", "Verkiezing Gemeenteraad 2026", "Tweede Kamer der Staten-Generaal in maart 2021".
ELECTION_TYPES = [
    ("GR", r"gemeente\s*raad|raad\s+van\s+de\s+gemeente"),
    ("TK", r"tweede\s*kamer"),
    ("PS", r"provinciale\s*staten"),
    ("EP", r"europees\s*parlement"),
    ("WS", r"waterschap"),
]
ELECTION_TYPE_RE = re.compile("|".join(f"(?P<{code}>{pattern})" for code, pattern in ELECTION_TYPES), re.IGNORECASE)
ELECTION_YEAR_RE = re.compile(r"\b(20\d\d)\b")
ELECTION_YEAR_WINDOW = 80
# Abbreviations such as "TK25" in the text ("De verkiezing van de leden van TK25") or "gr26" and "tk-2025" in file
# names, where they are sometimes glued to other words ("helvoirtgr26eerstetelling").
ELECTION_CODE_TEXT_RE = re.compile(r"\b(GR|TK|PS|EP|WS)\s?(?:20)?(\d\d)\b")
ELECTION_CODE_NAME_RE = re.compile(r"(gr|tk|ps|ep|ws)[-_ ]?(?:20)?(\d\d)(?!\d)", re.IGNORECASE)

class ResultMatch(StrEnum):
    """Best match type first"""

    CODE_TITLE = "code+title"
    TITLE = "title"
    CODE = "code"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"
    NONE = "none"

    @classmethod
    def members(cls):
        return [m for m in cls]

@dataclass
class ClassificationResult:
    model: str | None = None
    matched_on: ResultMatch = ResultMatch.UNKNOWN
    codes: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    found_by: str = ""
    text: str = ""
    region: dict[str, str] = field(default_factory=dict)
    election: tuple[str, str] = "", ""

@dataclass
class TitleMatch:
    model: str
    errors: int
    length: int
    start: int
    end: int

    def beaten_by(self, other: Self) -> bool:
        """Whether another title found at the same place fits better, or equally well and is longer."""
        if other is self or other.end <= self.start or self.end <= other.start:
            return False
        return (other.errors, -other.length) < (self.errors, -self.length)


class PvClassifier:

    def __init__(self, path: Path):
        self.path = path

    def render_page(self, index: int) -> Image.Image | None:
        pdf = pdfium.PdfDocument(self.path)
        try:
            if index >= len(pdf):
                return None
            # Filled-in form fields are only drawn once forms are initialized.
            pdf.init_forms()
            return pdf[index].render(scale=DPI / 72, grayscale=True).to_pil()
        finally:
            pdf.close()

    @staticmethod
    def ocr(image: Image.Image) -> str:
        return pytesseract.image_to_string(image, lang="nld", config="--psm 6")

    @staticmethod
    def rotate_upright(image: Image.Image) -> Image.Image | None:
        """Rotate a scan upright using Tesseract's orientation detection, or None if it is upright or unknown."""
        try:
            angle = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)["rotate"]
        except pytesseract.TesseractError:
            return None
        # OSD gives the clockwise correction; PIL rotates anticlockwise.
        return image.rotate(-angle, expand=True) if angle else None

    @staticmethod
    def find_codes(text: str) -> list[str]:
        codes = []
        for letter, number, suffix, sub in MODEL_RE.findall(text):
            number = number.translate(TO_DIGIT) + suffix + (f"-{sub.translate(TO_DIGIT)}" if sub else "")
            if letter:
                codes.append(f"{'I' if letter in I_LOOKALIKE else letter} {number}")
            else:
                # Without its letters a code only counts when its number belongs to a single known model.
                matches = [model for model in PV_CODES if model.split(" ")[1] == number]
                codes.append(matches[0] if len(matches) == 1 else number)
        return codes

    @staticmethod
    def find_titles(text: str) -> list[str]:
        """Return the models whose titles are on the page."""
        page = letters_only(text)
        found = []
        for key, pattern, model in TITLE_KEYS:
            if (start := page.find(key)) >= 0:
                found.append(TitleMatch(model, 0, len(key), start, start + len(key)))
            elif match := pattern.search(page):
                found.append(TitleMatch(model, sum(match.fuzzy_counts), len(key), *match.span()))
        # Similar titles match at the same place, like "… stembureaus" inside "… stembureaus die zijn herteld". Only the
        # best fit there counts.
        found = [m for m in found if not any(m.beaten_by(other) for other in found)]
        # A misread match for another PV than an exact one is text that merely resembles a title.
        exact = {pv_code(m.model) for m in found if not m.errors}
        return sorted({m.model for m in found if not m.errors or not exact or pv_code(m.model) in exact})

    def identify_model(self, text: str) -> ClassificationResult:
        """Decide the model from the codes and titles on the page, preferring no model over a doubtful one."""
        codes, titles = self.find_codes(text), self.find_titles(text)
        known = [code for code in codes if code in PV_CODES]
        # A bijlage page often repeats its PV's title; the bijlage title then decides.
        titles = [title for title in titles if not any(other != title and pv_code(other) == title for other in titles)]
        # Titles of different models on one page contradict each other, so a model is only decided by a single one.
        if len(titles) > 1:
            return ClassificationResult(None, ResultMatch.CONFLICT, codes, titles)
        if titles:
            if pv_code(titles[0]) in known:
                return ClassificationResult(titles[0], ResultMatch.CODE_TITLE, codes, titles)
            if known:
                return ClassificationResult(None, ResultMatch.CONFLICT, codes, titles)
            return ClassificationResult(titles[0], ResultMatch.TITLE, codes, titles)
        if known:
            return ClassificationResult(known[0], ResultMatch.CODE, codes, titles)
        return ClassificationResult(None, ResultMatch.UNKNOWN if codes else ResultMatch.NONE, codes, titles)

    @staticmethod
    def find_region(text: str) -> dict[str, str]:
        region = {}
        if match := GEMEENTE_RE.search(text):
            region["gemeente"] = match.group(1).zfill(4)
        if match := STEMBUREAU_RE.search(text):
            region["stembureau"] = match.group(1)
        if match := KIESKRING_RE.search(text):
            region["kieskring"] = match.group(1)
        return region

    def find_election(self, text: str) -> tuple[str, str]:
        """Return the election, e.g. "GR2026", and where it came from: the PDF text, the file name, or neither."""
        flat = " ".join(text.split())
        for match in ELECTION_TYPE_RE.finditer(flat):
            if year := ELECTION_YEAR_RE.search(flat, match.end(), match.end() + ELECTION_YEAR_WINDOW):
                return f"{match.lastgroup}{year.group(1)}", "pdf"
        if match := ELECTION_CODE_TEXT_RE.search(flat):
            return f"{match.group(1)}20{match.group(2)}", "pdf"
        # Bijlagen don't name the election on their first page.
        if match := ELECTION_CODE_NAME_RE.search(self.path.stem):
            return f"{match.group(1).upper()}20{match.group(2)}", "name"
        return "", ""

    def ocr_passes(self) -> Iterator[tuple[str, str]]:
        """Yield (pass, text) from cheapest to most expensive; later passes only run when asked for."""
        page = self.render_page(0)
        yield "crop", self.ocr(page.crop((0, 0, page.width, int(page.height * CROP_FRACTION))))
        full = self.ocr(page)
        yield "full", full
        if upright := self.rotate_upright(page):
            yield "rotated", self.ocr(upright)
        # Some GSB bijlagen have only a title on page 1 and the model on page 2; page 1 keeps the bijlage and region.
        if second := self.render_page(1):
            yield "page2", full + "\n" + self.ocr(second)

    def classify(self) -> ClassificationResult | None:
        """Run OCR passes until the model is identified; otherwise return the best-supported result of all passes."""
        best = None
        for found_by, text in self.ocr_passes():
            result = self.identify_model(text)
            result.found_by, result.text = found_by, text

            if best is None or ResultMatch.members().index(result.matched_on) < ResultMatch.members().index(
                best.matched_on
            ):
                best = result
            if result.matched_on in ("code+title", "title"):
                result.region = self.find_region(text)
                result.election = self.find_election(text)
                break
        return best
