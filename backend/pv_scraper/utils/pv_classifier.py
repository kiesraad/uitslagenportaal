"""POC: classify processen-verbaal by model and, where possible, region, using Tesseract on the first two pages.

A model counts as identified when its code and its title are both on the page, or its title alone. The classify_pvs
management command runs it on a folder of PDFs.
"""

import datetime
import logging
import re
import unicodedata
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Self

import pypdfium2 as pdfium
import pytesseract
import regex
from django.core.files.storage import storages
from PIL import Image
from pypdf import PdfWriter

from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from pv_scraper.models import ScrapeSource
from region.models import Region

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
}

# Texts that appear on one model only, from the forms the Kiesraad published on 27 November 2025 as OSV fills them in;
# the O 7, P 1f-1 and P 22-1 forms have no newer version. Forms of earlier elections word and number things
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


def uncompact(line: str, index: int) -> str:
    """The first part of a string, up to the position `index`, but in its spaceless form."""
    seen = 0
    for i, char in enumerate(line):
        if not char.isspace():
            if seen == index:
                return line[:i]
            seen += 1
    return line


def pv_code(model: str) -> str:
    """The code printed on the page: a bijlage carries the code of the PV it belongs to."""
    return model.split(" Bijlage")[0]


PV_CODES = {pv_code(model) for model in MODELS}


def pv_model_short_form(model: str) -> str:
    """The model as written in a file name: "N 10-2" is "N10-2", "Na 31-2 Bijlage 1" is "Na31-2-B1"."""
    code, _, bijlage = model.partition(" Bijlage ")
    return code.replace(" ", "") + (f"-B{bijlage}" if bijlage else "")


# How a model was decided, best first. Only the first two count as identified.
BASES = ["code+title", "title", "code", "conflict", "unknown", "none"]

# OCR mixes up digits and letters ("Model N I0-z", "Modei"), drops spaces ("ModelNa31-2") and sometimes the letters
# ("Model 31-1").
OCR_DIGIT = "[0-9IlOoz]"
MODEL_RE = re.compile(
    rf"(?i:\bmode[li1])\s*(?:([A-Z][a-z]?)\s*-?)?"
    rf"\s*({OCR_DIGIT}{{1,2}})([a-z](?![a-z]))?(?:\s*[-–—~.]\s*({OCR_DIGIT}))?"
)
TO_DIGIT = str.maketrans("IlOoz", "11002")

# A gemeente name has no digits and is short, unlike prose; OCR may curl the quote of "'s-Hertogenbosch".
GEMEENTE_NAME = r"(?:['‘’]s[- ])?[A-Z][^\d\n]{1,40}?"
# A dash may separate the name from what follows it: "Gemeente 0762 Deurne — Stembureau 10".
NAME_END = r"[ \t]*(?:[-–—][ \t]*)?"
# The name may follow the code to the end of the line or up to the stembureau: "Gemeente 0899 Brunssum Stembureau 13".
GEMEENTE_RE = re.compile(
    rf"(?i:gemeente)[:\s]*(\d{{3,4}})\b(?:[ \t]+({GEMEENTE_NAME})(?={NAME_END}(?:Stembureau|$)))?",
    re.MULTILINE,
)
# OSV headers put the name, with or without its code, on the line above the stembureau: "1659 Laarbeek\nCentraal
# Stembureau", "Moerdijk\nStembureau". OCR can drop the code's leading zero ("373 Bergen (NH)").
GEMEENTE_HEADER_RE = re.compile(
    rf"^[ \t]*(?:(\d{{3,4}})[ \t]+|Gemeente[ \t]+)?(?!(?i:.*stembureau))({GEMEENTE_NAME}){NAME_END}\n\s*"
    r"(?:(?:Centraal|Gemeentelijk)[ \t]+[Ss]|S)tembureau\b",
    re.MULTILINE,
)
STEMBUREAU_RE = re.compile(r"(?i:stembureau(?:nummer)?|nummer\s*stembureau)[-:\s]*(?i:nr\.?|nummer)?[:\s]*(\d{1,4})\b")
KIESKRING_RE = re.compile(r"(?i:kieskring)[:\s]*(\d{1,2})\b")

# Models that belong to one stembureau; only for these does a number in the filename name the stembureau.
STEMBUREAU_MODELS = {"N 10-1", "N 10-2", "Na 14-1", "Na 31-2 Bijlage 1"}
# Models of a centraal stembureau. They name no gemeente; their region is the CSB, which for GR is the gemeente.
CSB_MODELS = {"P 22-1", "P 22-2"}
# A stembureau in a file name: the common "<gemeente>_<nummer>_<locatie>_GR26" ("Brunssum_10_…") first, as the location
# may itself contain "stembureau 1"; else "stembureau_7_…", "sb35_1", "1680_Bijlagen 1 en 2_Stembureau_22_…". Other
# numbers, such as dates or a leading gemeente code, are left alone, and stembureaus are numbered from 1.
STEMBUREAU_CONVENTION_RE = re.compile(r"^(?!(?i:bijlage|model|pv)_)[A-Za-z][^_\d]*_+0*([1-9]\d{0,3})_")
STEMBUREAU_NAME_RE = re.compile(r"(?i)(?<![a-z])(?:stembureau|sb)[-_ ]*0*([1-9]\d{0,3})(?!\d)")
# The heading that starts a stembureau's section in a Na 31-2 bijlage 1: "Stembureau 12" on a line of its own, with the
# stembureau's name on the next. The running header at the top of the page is no heading.
SECTION_STEMBUREAU_RE = re.compile(
    r"^[ \t]*Stembureau[ \t]+(\d{1,4})[ \t]*\n\s*"
    r"(?!(?i:stembureau|bijlage|over\s+deze|gemeente|b1\b))(?:[^\W\d_]|['‘’])",
    re.MULTILINE,
)

# The election is named with its year a few words later: "de leden van de gemeenteraad van Brummen op 18 maart
# 2026", "Verkiezing Gemeenteraad 2026", "Tweede Kamer der Staten-Generaal in maart 2021". The patterns also match
# with the spaces removed. A waterschap election is AB (algemeen bestuur), as in its EML election identifier.
ELECTION_TYPES = [
    ("GR", r"gemeente\s*raad|raad\s*van\s*de\s*gemeente"),
    ("TK", r"tweede\s*kamer"),
    ("PS", r"provinciale\s*staten"),
    ("EP", r"europees\s*parlement"),
    ("AB", r"waterschap|hoogheemraadschap|wetterskip"),
]
ELECTION_TYPE_RE = re.compile("|".join(f"(?P<{code}>{pattern})" for code, pattern in ELECTION_TYPES), re.IGNORECASE)
ELECTION_YEAR_RE = re.compile(r"\b(20\d\d)\b")
ELECTION_YEAR_WINDOW = 80
# Abbreviations such as "TK25" in the text ("De verkiezing van de leden van TK25") or "gr26" and "tk-2025" in file
# names, where they are sometimes glued to other words ("helvoirtgr26eerstetelling"). WS stands for AB too.
ELECTION_CODE_TEXT_RE = re.compile(r"\b(GR|TK|PS|EP|AB|WS)\s?(?:20)?(\d\d)\b")
ELECTION_CODE_NAME_RE = re.compile(r"(gr|tk|ps|ep|ab|ws)[-_ ]?(?:20)?(\d\d)(?!\d)", re.IGNORECASE)


def election_code(abbreviation: str, year: str) -> str:
    """The election id for an abbreviation and two-digit year: ("ws", "27") is "AB2027"."""
    code = abbreviation.upper()
    return f"{'AB' if code == 'WS' else code}20{year}"


# OSV forms name the election and its date in the header, just above the title and model code: "Verkiezing
# Gemeenteraad 2026 woensdag 18 maart 2026", "De verkiezing van de leden van de gemeenteraad\n18 maart 2026". OCR
# splits words and misreads letters there ("Gemeentera ad", "ma art", "maarl2o26"), so the date is read with the
# spaces removed and a month may have one misread letter after its first.
MONTHS = [
    "januari",
    "februari",
    "maart",
    "april",
    "mei",
    "juni",
    "juli",
    "augustus",
    "september",
    "oktober",
    "november",
    "december",
]
HEADER_DATE_RE = regex.compile(
    rf"(?e)(?P<day>[0-3]?\d)?(?:{'|'.join(f'(?P<m{i}>{m[0]}(?:{m[1:]}){{e<=1}})' for i, m in enumerate(MONTHS))})"
    rf"(?P<year>2{OCR_DIGIT}{{3}})"
)
HEADER_LABEL_START_RE = re.compile(rf"(?i:\b(?:de\s+)?verkiezing)|{ELECTION_TYPE_RE.pattern}", re.IGNORECASE)
# What may trail the label before the date: a weekday, "van", "op" or "in", and OCR debris such as the "1 B" of
# "1 B maart".
HEADER_LABEL_TAIL_RE = re.compile(
    r"(?:\s+(?:(?:maan|dins|woens|donder|vrij|zater|zon)dag|van|op|in|\S?\d\S?|\S))*[\s,.\-–—]*$", re.IGNORECASE
)
YEAR_IN_COMPACT_RE = re.compile(r"(?<!\d)(20\d\d)(?!\d)")
# The authority an election is for follows its body in the label: "de gemeenteraad van Ede", "Provinciale Staten
# Drenthe 2027", "het algemeen bestuur van het hoogheemraadschap van Delfland". TK and EP have one election per id.
AUTHORITY_RES = {
    "GR": re.compile(r"gemeente\s*raad(?:s?verkiezing)?\s+(?:van\s+(?:de\s+gemeente\s+)?)?(?P<name>.+)", re.I),
    "PS": re.compile(r"provinciale\s*staten(?:verkiezing)?\s+(?:van\s+(?:de\s+provincie\s+)?)?(?P<name>.+)", re.I),
    "AB": re.compile(r"(?:waterschap|hoogheemraadschap|wetterskip)(?:sverkiezing)?\s+(?:van\s+)?(?P<name>.+)", re.I),
}
# A name ends at a year or at the "d.d." (de dato) before a date: "Gemeenteraad 2026 woensdag 18 maart", "Castricum
# d.d. 18 maart 2026".
AUTHORITY_END_RE = re.compile(r"\s*(?:\b20\d\d\b|\bd\.\s?d\b).*$", re.IGNORECASE)
# Characters OCR makes of form lines and boxes: "de gemeenteraad van | Brummen".
OCR_STRAY_RE = re.compile(r"[|\[\]{}_~]")
# The provinces and waterschappen, named as in their EML; the authority a PS or AB header names is corrected to one of
# these, or dropped. Update after a merger.
AUTHORITIES = {
    "PS": [
        "Groningen",
        "Fryslân",
        "Drenthe",
        "Overijssel",
        "Flevoland",
        "Gelderland",
        "Utrecht",
        "Noord-Holland",
        "Zuid-Holland",
        "Zeeland",
        "Noord-Brabant",
        "Limburg",
    ],
    "AB": [
        "Noorderzijlvest",
        "Fryslân",
        "Hunze en Aa's",
        "Drents Overijsselse Delta",
        "Vechtstromen",
        "Vallei en Veluwe",
        "Rijn en IJssel",
        "De Stichtse Rijnlanden",
        "Amstel, Gooi en Vecht",
        "Hollands Noorderkwartier",
        "Rijnland",
        "Delfland",
        "Schieland en de Krimpenerwaard",
        "Rivierenland",
        "Hollandse Delta",
        "Scheldestromen",
        "Brabantse Delta",
        "De Dommel",
        "Aa en Maas",
        "Limburg",
        "Zuiderzeeland",
    ],
}
# The source kind whose name is the authority of an election type, when the header doesn't name it.
# The CSB of a national election, which has one for the whole country.
NATIONAL_CSBS = {"TK": "Nederland", "EP": "Nederland"}
AUTHORITY_SOURCE_KINDS = {"PS": RegionCategory.PROVINCIE, "AB": RegionCategory.WATERSCHAP}

# Document information keys under which a stored PV carries the fields of its PvIdentity.
PDF_METADATA_KEYS = {
    "election": "/PvElection",
    "election_date": "/PvElectionDate",
    "model": "/PvModel",
    "csb": "/PvCsb",
    "region_code": "/PvRegionCode",
    "region_name": "/PvRegionName",
    "stembureau": "/PvStembureau",
    "matched_on": "/PvMatchedOn",
}

logger = logging.getLogger(__name__)


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

    def is_certain(self):
        return self in (self.CODE_TITLE, self.TITLE)


@dataclass
class PvRegion:
    """Region numbers and name read from a PV; empty when not on the page."""

    code: str = ""
    name: str = ""
    stembureau: str = ""
    kieskring: str = ""


@dataclass
class PvElection:
    """Election read from a PV, and where it was found: "header", "pdf", "name", or empty when not found.

    The authority is the gemeente, province or waterschap the header names the election for ("Aa en Maas"), or empty.
    It is the name of the election's CSB, which tells apart elections of one id.
    """

    id: str = ""
    date: datetime.date | None = None
    authority: str = ""
    found_in: str = ""


@dataclass
class ClassificationResult:
    model: str | None = None
    matched_on: ResultMatch = ResultMatch.UNKNOWN
    codes: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    found_by: str = ""
    text: str = ""
    region: PvRegion = field(default_factory=PvRegion)
    election: PvElection = field(default_factory=PvElection)


@dataclass
class PvIdentity:
    """What a classified PV is, for its file name and metadata; empty values are unknown."""

    election: str
    election_date: str
    model: str
    csb: str
    region_code: str
    region_name: str
    stembureau: str
    matched_on: str


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


class PvClassificationException(Exception):
    """Error during classification of a PV."""


class PvClassifier:
    def __init__(self, file: Path | NamedBytesIO):
        self.file = NamedBytesIO.from_path(file) if isinstance(file, Path) else file
        self.result: ClassificationResult | None

    def render_page(self, index: int) -> Image.Image | None:
        pdf = pdfium.PdfDocument(self.file)
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
        return pytesseract.image_to_string(image, lang="nld", config="--psm 3")

    def page_text(self, index: int) -> str:
        """The OCR text of a whole page, or empty when the PDF is shorter."""
        page = self.render_page(index)
        return self.ocr(page) if page else ""

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
                codes.append(f"{letter} {number}")
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
    def find_region(text: str) -> PvRegion:
        region = PvRegion()
        # The gemeente is read from a "Gemeente 0888" line first, then from the header above the stembureau.
        matches = [m for m in (GEMEENTE_RE.search(text), GEMEENTE_HEADER_RE.search(text)) if m]
        # The gemeente code from the found texts, padded to four digits.
        if code := next((m.group(1) for m in matches if m.group(1)), None):
            region.code = code.zfill(4)
        # The gemeente name from the found texts
        if name := next((m.group(2) for m in matches if m.group(2)), None):
            region.name = name
        # The stembureau number from the first "Stembureau [number]" in the text.
        if match := STEMBUREAU_RE.search(text):
            region.stembureau = match.group(1)
        # The kieskring number from the first "Kieskring [number]" in the text.
        if match := KIESKRING_RE.search(text):
            region.kieskring = match.group(1)
        return region

    @staticmethod
    def find_section_stembureau(text: str) -> str:
        return match.group(1) if (match := SECTION_STEMBUREAU_RE.search(text)) else ""

    @staticmethod
    def find_stembureau_in_name(stem: str) -> str:
        match = STEMBUREAU_CONVENTION_RE.search(stem) or STEMBUREAU_NAME_RE.search(stem)
        return match.group(1) if match else ""

    @staticmethod
    def find_header_election(text: str) -> PvElection | None:
        """
        Read the election from the header lines above the model code, or None if they don't name one.

        The label naming the election runs from the last line saying "verkiezing" (or else naming an election type) up
        to the date, which may be on a following line. Only its authority is kept, as labels are worded in many ways.
        """
        # The header is the non-blank lines above the model code.
        if not (code := MODEL_RE.search(text)):
            return None
        lines = [line for line in text[: code.start()].splitlines() if line.strip()]

        # Find the line the label starts on, comparing lines without spaces as OCR splits words ("Gemeentera ad").
        compacts = ["".join(line.split()).lower() for line in lines]
        start = next((i for i in reversed(range(len(lines))) if "verkiezing" in compacts[i]), None)
        if start is None:
            start = next((i for i in reversed(range(len(lines))) if ELECTION_TYPE_RE.search(compacts[i])), None)
        if start is None:
            return None

        # Cut the label at the date, searched for in the start line and the two after it, as the label and the date
        # itself may wrap: "…gemeenteraad van 18\nmaart 2026". Without a date, the label is the start line.
        block = "\n".join(lines[start : start + 3])
        if date_match := HEADER_DATE_RE.search("".join(block.split()).lower()):
            label = uncompact(block, date_match.start())
        else:
            label = lines[start]

        # Trim the label to run from "verkiezing" or the election type up to the weekday and debris before the date.
        label = " ".join(label.split())
        if match := HEADER_LABEL_START_RE.search(label):
            label = label[match.start() :]
        label = HEADER_LABEL_TAIL_RE.sub("", label)

        # Read the election type from the label, and the year from the date or else from the label.
        compact_label = "".join(label.split()).lower()
        if not (election_type := ELECTION_TYPE_RE.search(compact_label)):
            return None
        if date_match:
            year = date_match.group("year").translate(TO_DIGIT)
        elif year_match := YEAR_IN_COMPACT_RE.search(compact_label):
            year = year_match.group(1)
        else:
            return None

        # Keep the full date only when its day was read and it is a valid date.
        date = None
        if date_match and date_match.group("day"):
            month = next(i for i in range(len(MONTHS)) if date_match.group(f"m{i}")) + 1
            try:
                date = datetime.date(int(year), month, int(date_match.group("day")))
            except ValueError:
                pass
        authority = PvClassifier.find_authority(election_type.lastgroup, label)
        return PvElection(f"{election_type.lastgroup}{year}", date, authority, "header")

    @staticmethod
    def find_authority(election_type: str, label: str) -> str:
        """The gemeente, province or waterschap a label names the election for, or empty."""
        # Find the name after the election's body, in the label without OCR's form lines; TK and EP name none.
        pattern = AUTHORITY_RES.get(election_type)
        if not pattern or not (match := pattern.search(" ".join(OCR_STRAY_RE.sub(" ", label).split()))):
            return ""

        # Cut the name at the year or date and the words before it, and strip the punctuation around it.
        name = HEADER_LABEL_TAIL_RE.sub("", AUTHORITY_END_RE.sub("", match.group("name")))
        name = name.strip(" ,.:;-–—")
        if not letters_only(name) or "verkiezing" in letters_only(name):
            return ""

        # A province or waterschap is corrected to its known spelling; a gemeente is kept as read.
        if election_type in AUTHORITIES:
            return PvClassifier.known_authority(election_type, name)
        return name

    @staticmethod
    def known_authority(election_type: str, name: str) -> str:
        """The province or waterschap a name stands for, spelled as in AUTHORITIES, or empty."""
        return next((known for known in AUTHORITIES[election_type] if PvClassifier.authority_matches(known, name)), "")

    def find_election(self, text: str) -> PvElection:
        """Return the election, preferring the header over the rest of the text, and the text over the file name."""
        # The header above the model code, which also gives the date and authority.
        if election := self.find_header_election(text):
            return election

        # The first election type anywhere in the text with a year shortly after it, line breaks read as spaces.
        flat = " ".join(text.split())
        for match in ELECTION_TYPE_RE.finditer(flat):
            if year := ELECTION_YEAR_RE.search(flat, match.end(), match.end() + ELECTION_YEAR_WINDOW):
                return PvElection(f"{match.lastgroup}{year.group(1)}", found_in="pdf")

        # An abbreviation such as "TK25" in the text.
        if match := ELECTION_CODE_TEXT_RE.search(flat):
            return PvElection(election_code(*match.groups()), found_in="pdf")

        # An abbreviation such as "gr26" in the file name, as bijlagen don't name the election on their first page.
        if match := ELECTION_CODE_NAME_RE.search(self.file.stem):
            return PvElection(election_code(*match.groups()), found_in="name")
        return PvElection()

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
        """Run OCR passes until the model is identified; otherwise return None."""
        best = None
        for found_by, text in self.ocr_passes():
            result = self.identify_model(text)
            result.found_by, result.text = found_by, text

            if best is None or ResultMatch.members().index(result.matched_on) < ResultMatch.members().index(
                best.matched_on
            ):
                best = result
            if result.matched_on in (ResultMatch.CODE_TITLE, ResultMatch.TITLE):
                result.region = self.find_region(text)
                if result.model == "Na 31-2 Bijlage 1":
                    # The running header may repeat one stembureau on every page (Ede GR2026); the section heading
                    # names the right one, on page 1 or after a cover page on page 2.
                    if section := self.find_section_stembureau(text) or self.find_section_stembureau(self.page_text(1)):
                        result.region.stembureau = section
                if result.model in STEMBUREAU_MODELS and not result.region.stembureau:
                    result.region.stembureau = self.find_stembureau_in_name(self.file.stem)
                result.election = self.find_election(text)
                break

        self.result = best
        return self.result

    @staticmethod
    def slug(name: str) -> str:
        """A name for a file name: ASCII lowercase, with hyphens kept and other separators made hyphens.

        "Súdwest-Fryslân" is "sudwest-fryslan", "'s-Hertogenbosch" "s-hertogenbosch", "Hunze en Aa's" "hunze-en-aas",
        "Bergen (NH)" "bergen-nh". An apostrophe is dropped rather than separating, and "_" never appears.
        """
        ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
        return re.sub(r"[^a-z0-9]+", "-", re.sub(r"['‘’`]", "", ascii_name)).strip("-")

    @staticmethod
    def authority_matches(name: str, authority: str) -> bool:
        """Whether a name is the authority read from a PV, ignoring case, accents, spacing and one misread letter."""
        key, other = letters_only(name), letters_only(authority)
        return key == other or (len(key) >= 6 and regex.fullmatch(f"(?:{key}){{e<=1}}", other) is not None)

    @classmethod
    def complete_gemeente(cls, code: str, name: str) -> tuple[str, str]:
        """
        The code and name of a gemeente, with the name as in the most recent election that has the gemeente. Without a
        code, the name is matched as an authority is, preferring an exact match over one with a misread letter.
        Unknown gemeenten keep what was given.
        """
        regions = Region.objects.filter(region_category=RegionCategory.GEMEENTE).order_by("-election__date")
        if code:
            region_name = regions.filter(region_number=code.lstrip("0")).values_list("region_name", flat=True).first()
            return code, region_name or name
        if not name:
            return code, name
        rows = list(regions.values_list("region_number", "region_name"))
        key = letters_only(name)
        match = next((row for row in rows if letters_only(row[1]) == key), None)
        match = match or next((row for row in rows if cls.authority_matches(row[1], name)), None)
        return match or (code, name)

    def is_csb_pv(self) -> bool:
        """Whether the PV is about a CSB rather than a gemeente: a CSB model of an election other than GR."""
        election_type = self.result.election.id[:2]
        return self.result.model in CSB_MODELS and (election_type in AUTHORITIES or election_type in NATIONAL_CSBS)

    def identity(self, csb: str = "", region_code: str = "", region_name: str = "") -> PvIdentity:
        """What the PV is; the arguments override what was read from the PV."""
        result = self.result
        if result is None or not result.model or not result.election.id:
            raise PvClassificationException("Cannot name file: model or election not known")

        election_type = result.election.id[:2]
        if election_type in NATIONAL_CSBS:
            csb = NATIONAL_CSBS[election_type]
        else:
            csb = (csb or result.election.authority) if election_type in AUTHORITIES else ""

        # Check if PV is a CSB PV (but not a municipality PV)
        if self.is_csb_pv():
            if not csb:
                raise PvClassificationException("Cannot name file: CSB not known")
            code, name = "", csb
        else:
            code, name = self.complete_gemeente(region_code or result.region.code, region_name or result.region.name)

        if not code and not name:
            raise PvClassificationException("Cannot name file: region not known")

        stembureau = result.region.stembureau if result.model in STEMBUREAU_MODELS else ""
        # A wrong stembureau would replace another stembureau's PV, so the PV and its file name must agree.
        if stembureau and (in_name := self.find_stembureau_in_name(self.file.stem)) and in_name != stembureau:
            raise PvClassificationException(
                f"Cannot name file: stembureau {stembureau} in the PV but {in_name} in its file name"
            )

        return PvIdentity(
            election=result.election.id,
            election_date=result.election.date.isoformat() if result.election.date else "",
            model=pv_model_short_form(result.model),
            csb=csb,
            region_code=code.zfill(4) if code else "",
            region_name=name,
            stembureau=stembureau,
            matched_on=str(result.matched_on),
        )

    def storage_name(self, csb: str = "", region_code: str = "", region_name: str = "") -> str:
        """
        The file name of the PV: "<election>_<model>[_<csb>]_<region>[_SB<n>].pdf".

        The CSB is the province or waterschap of a PS or AB election; "Nederland" of TK and EP is the same for every PV
        and left out. The region is the gemeente as "<code>-<name>", or the CSB itself for a CSB model. Both are slugs,
        so "_" only separates parts, and a last part "SB<n>" is the stembureau of a stembureau model.
        """
        pv = self.identity(csb, region_code, region_name)
        parts = [
            pv.election,
            pv.model,
            self.slug(pv.csb) if pv.election[:2] in AUTHORITIES and not self.is_csb_pv() else "",
            "-".join(filter(None, [pv.region_code, self.slug(pv.region_name)])),
            f"SB{pv.stembureau}" if pv.stembureau else "",
        ]
        return "_".join(filter(None, parts)) + ".pdf"

    def add_metadata_to_pv(self, csb: str = "", region_code: str = "", region_name: str = "") -> NamedBytesIO:
        """
        The PDF with what the PV is in its document information, added as an incremental update.

        The original bytes stay in front unchanged, so a digital signature stays valid and the published file can be
        recovered. Title and subject show in any viewer; the "/Pv…" keys are for software.
        """
        pv = self.identity(csb, region_code, region_name)
        stembureau = f"stembureau {pv.stembureau}" if pv.stembureau else ""
        metadata = {
            "/Title": " ".join(filter(None, [pv.model, pv.region_name or pv.region_code, stembureau])),
            "/Subject": " ".join(filter(None, [pv.election, pv.csb])),
            **{PDF_METADATA_KEYS[key]: value for key, value in asdict(pv).items() if value},
        }
        self.file.seek(0)
        writer = PdfWriter(self.file, incremental=True)
        writer.add_metadata(metadata)
        output = NamedBytesIO(b"", self.file.path)
        writer.write(output)
        output.seek(0)
        return output

    def save_to_storage(self, source: ScrapeSource, folder: str) -> str:
        """Store the PV with its metadata under its name in a folder, replacing a file of that name, and return the
        storage key.

        A PV found on a gemeente's website must be about that gemeente, unless its region is a province or waterschap;
        the source then also gives the gemeente's name, and that of a waterschap or province the CSB.
        """
        if self.result is None:
            raise PvClassificationException("Cannot save file: not classified")

        # What the source tells about the PV overrides what was read from it; empty keeps what was read.
        election, region = self.result.election, self.result.region
        csb = region_code = region_name = ""

        # A gemeente's website gives the gemeente, which the gemeente read from the PV must match by code or name.
        if source.kind == RegionCategory.GEMEENTE and not self.is_csb_pv():
            region_code, region_name = source.code.removeprefix("gm"), source.name
            if region.code != region_code and not self.authority_matches(source.name, region.name):
                raise PvClassificationException(f"Cannot save file: PV is not from {source}")

            # The gemeenteraad a GR header names must be that gemeente's too.
            if election.id.startswith("GR") and election.authority:
                if not self.authority_matches(source.name, election.authority):
                    raise PvClassificationException(f"Cannot save file: PV is from {election.authority}")

        # A province's or waterschap's website gives the CSB of a PS or AB election, spelled as in AUTHORITIES.
        elif source.kind == AUTHORITY_SOURCE_KINDS.get(election.id[:2]):
            csb = self.known_authority(election.id[:2], source.name)

        # Name the PV and add what it is to its PDF metadata.
        key = f"{folder}/{self.storage_name(csb, region_code, region_name)}"
        content = self.add_metadata_to_pv(csb, region_code, region_name)

        # Replace a file of the same name, which storage would otherwise keep, saving this one under a suffixed name.
        storage = storages["default"]
        if storage.exists(key):
            storage.delete(key)
        return storage.save(key, content)
