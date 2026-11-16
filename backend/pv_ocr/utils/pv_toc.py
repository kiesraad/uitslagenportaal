"""POC: determine the table of contents of a PV from the header of each page, using Tesseract.

Only the top of each page is read; the headings that tell what a page holds sit there. The determine_pv_toc management
command runs it on a folder of PDFs.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple

import pypdfium2 as pdfium
import regex
from PIL import Image

from file_import.utils.named_bytes_io import NamedBytesIO
from pv_ocr.utils.pv_classifier import OCR_DIGIT, TO_DIGIT, PvClassifier, letters_only
from pv_ocr.utils.rendering import render_scale

# The share of each page, from the top, that is read. Headings of vote-count pages sit within the top fifth; reading
# more gives false matches from the body.
HEADER_FRACTION = 0.2

# The body of a page, as shares of its height from the top, and the share of its width cut off on both sides (punch
# holes). The band starts below the running header, but high enough to keep a continuation of one or two candidates.
BODY_BAND = (0.15, 0.85)
BODY_SIDE_MARGIN = 0.08
BODY_DPI = 100
# A page is empty when the inkiest strip of its body, of this share of the page height, stays under the limit. The
# strip, not the band average, catches a short continuation. Ink is a pixel darker than the grey level.
BODY_STRIP_HEIGHT = 0.025
EMPTY_STRIP_INK_SHARE = 0.005
INK_GREY_LEVEL = 200


class PageContent(StrEnum):
    COVER = "cover"  # Cover page
    TABLE_OF_CONTENTS = "table-of-contents"  # Table of contents (Inhoudsopgave)
    CHECKS_AND_CORRECTIONS = "checks-and-corrections"  # Checks and corrections of the counts
    SESSION_REPORT = "session-report"  # Report of the session: attendance, events, objections, recounts
    ABOUT_ATTACHMENT = "about-attachment"  # Introduction to a bijlage (Over deze bijlage)
    ADMITTED_VOTERS = "admitted-voters"  # Admitted voters (A–D)
    VOTES_CAST = "votes-cast"  # Votes cast per list and in total (E–H)
    DIFFERENCES = "differences"  # Differences between admitted voters and votes cast (I, J)
    LIST_DIFFERENCES = "list-differences"  # Lists whose counts differ
    CANDIDATE_VOTES = "candidate-votes"  # Votes per candidate of one list
    CANDIDATE_VOTES_CONTINUED = "candidate-votes-continued"  # Votes per candidate of one list, continued
    INVESTIGATION = "investigation"  # Investigation of the counts
    ELECTORATE = "electorate"  # Number of electors (kiesgerechtigden)
    SEAT_ALLOCATION = "seat-allocation"  # Seat allocation: kiesdeler, full and remaining seats, seats to candidates
    ELECTED_CANDIDATES = "elected-candidates"  # Elected candidates in alphabetical order
    EMPTY_PAGE = "empty-page"  # Blank page, or one left empty on purpose
    SIGNATURES = "signatures"  # Signatures (ondertekening)
    UNKNOWN = "unknown"  # Not recognized


# The contents that hold the vote counts a PV reports.
VOTE_COUNT_CONTENTS = {
    PageContent.ELECTORATE,
    PageContent.ADMITTED_VOTERS,
    PageContent.VOTES_CAST,
    PageContent.DIFFERENCES,
    PageContent.CANDIDATE_VOTES,
    PageContent.CANDIDATE_VOTES_CONTINUED,
}
LIST_CONTENTS = (PageContent.CANDIDATE_VOTES, PageContent.CANDIDATE_VOTES_CONTINUED)

# The contents each model has, following the Kiesraad templates (Nov 2025) and the test set. A cover, an empty page and
# an unknown page can occur in any model.
_EVERY_MODEL = {PageContent.COVER, PageContent.EMPTY_PAGE, PageContent.UNKNOWN}
_COUNTS = {PageContent.ADMITTED_VOTERS, PageContent.VOTES_CAST, PageContent.DIFFERENCES}
# What a PV with a session report, counts and lists has.
_FULL_PV = {
    PageContent.TABLE_OF_CONTENTS,
    PageContent.CHECKS_AND_CORRECTIONS,
    PageContent.SESSION_REPORT,
    PageContent.ELECTORATE,
    PageContent.SIGNATURES,
    *_COUNTS,
    *LIST_CONTENTS,
}
_SEATS = {PageContent.SEAT_ALLOCATION, PageContent.ELECTED_CANDIDATES}
MODEL_CONTENTS = {
    model: frozenset(_EVERY_MODEL | contents)
    for model, contents in {
        "N 10-1": {
            PageContent.CHECKS_AND_CORRECTIONS,
            PageContent.SESSION_REPORT,
            PageContent.SIGNATURES,
            *_COUNTS,
            *LIST_CONTENTS,
        },
        "N 10-2": {PageContent.TABLE_OF_CONTENTS, PageContent.SESSION_REPORT, PageContent.SIGNATURES, *_COUNTS},
        "Na 14-1": {
            PageContent.TABLE_OF_CONTENTS,
            PageContent.INVESTIGATION,
            PageContent.LIST_DIFFERENCES,
            PageContent.SIGNATURES,
            *_COUNTS,
            *LIST_CONTENTS,
        },
        "Na 14-2": {
            PageContent.TABLE_OF_CONTENTS,
            PageContent.ELECTORATE,
            PageContent.SIGNATURES,
            *_COUNTS,
            *LIST_CONTENTS,
        },
        "Na 14-2 Bijlage 1": {
            PageContent.ABOUT_ATTACHMENT,
            PageContent.CHECKS_AND_CORRECTIONS,
            PageContent.INVESTIGATION,
            *_COUNTS,
            *LIST_CONTENTS,
        },
        "Na 31-1": _FULL_PV,
        "Na 31-2": _FULL_PV,
        "Na 31-2 Bijlage 1": {
            PageContent.ABOUT_ATTACHMENT,
            PageContent.INVESTIGATION,
            PageContent.LIST_DIFFERENCES,
            *_COUNTS,
            *LIST_CONTENTS,
        },
        "O 7": _FULL_PV,
        "P 1f-1": _FULL_PV - {PageContent.SESSION_REPORT},
        "P 22-1": _FULL_PV | _SEATS,
        "P 22-2": _FULL_PV | _SEATS,
    }.items()
}

# Heading titles by content. Section numbers differ per model ("2.2", "B1 - 3.2"), so only the words are matched.
HEADING_TITLES = [
    ("Inhoudsopgave", PageContent.TABLE_OF_CONTENTS),
    ("Controles en correcties", PageContent.CHECKS_AND_CORRECTIONS),
    ("Is er een gecorrigeerde uitslag", PageContent.CHECKS_AND_CORRECTIONS),
    ("Controles in opdracht van het centraal stembureau", PageContent.CHECKS_AND_CORRECTIONS),
    ("Hoe zijn de gecorrigeerde telresultaten tot stand gekomen", PageContent.CHECKS_AND_CORRECTIONS),
    ("Totstandkoming van dit corrigendum", PageContent.CHECKS_AND_CORRECTIONS),
    ("Waarom dit corrigendum", PageContent.CHECKS_AND_CORRECTIONS),
    ("Presentielijst", PageContent.SESSION_REPORT),
    ("Tijdens het stemmen", PageContent.SESSION_REPORT),
    ("Tijdens het tellen", PageContent.SESSION_REPORT),
    ("Tijdens de zitting", PageContent.SESSION_REPORT),
    ("Fouten of vermoedens van fouten", PageContent.SESSION_REPORT),
    ("Meldingen van belangstellenden", PageContent.SESSION_REPORT),
    ("Verslag van controlewerkzaamheden", PageContent.SESSION_REPORT),
    ("Verslag controlewerkzaamheden", PageContent.SESSION_REPORT),
    ("Bezwaren", PageContent.SESSION_REPORT),
    ("Bijzonderheden", PageContent.SESSION_REPORT),
    ("Ingeleverde kandidatenlijsten", PageContent.SESSION_REPORT),
    ("Overzicht kieskringen met plaats van het hoofdstembureau", PageContent.SESSION_REPORT),
    ("Hertelling", PageContent.SESSION_REPORT),
    ("Over deze bijlage", PageContent.ABOUT_ATTACHMENT),
    ("Extra onderzoek", PageContent.INVESTIGATION),
    ("Aantallen kiezers en stemmen", PageContent.INVESTIGATION),
    ("Tel de stembiljetten", PageContent.INVESTIGATION),
    ("Verklaringen vanuit het stembureau", PageContent.INVESTIGATION),
    ("Aantal kiesgerechtigden", PageContent.ELECTORATE),
    ("Toegelaten kiezers", PageContent.ADMITTED_VOTERS),
    ("Uitgebrachte stemmen", PageContent.VOTES_CAST),
    ("Verschillen tussen aantal kiezers en uitgebrachte stemmen", PageContent.DIFFERENCES),
    ("Lijsten met verschillen", PageContent.LIST_DIFFERENCES),
    ("Tellingen op lijstniveau", PageContent.LIST_DIFFERENCES),
    ("Stemmen per lijst en per kandidaat", PageContent.CANDIDATE_VOTES),
    ("Kiesdeler", PageContent.SEAT_ALLOCATION),
    ("Aantal volle zetels per lijst", PageContent.SEAT_ALLOCATION),
    ("Restzetels", PageContent.SEAT_ALLOCATION),
    ("Verdeling van de zetels", PageContent.SEAT_ALLOCATION),
    ("Toewijzing van zetels aan kandidaten", PageContent.SEAT_ALLOCATION),
    ("Gekozen kandidaten in alfabetische volgorde", PageContent.ELECTED_CANDIDATES),
    ("Met voorkeursstemmen gekozen kandidaten", PageContent.SEAT_ALLOCATION),
    ("Uitkomst controleprotocol", PageContent.CHECKS_AND_CORRECTIONS),
    ("Deze pagina is expres leeg", PageContent.EMPTY_PAGE),
]
# Part titles also print in the running header of every page of their part, above the section heading. They only
# decide when no section title is found, and the first in this list that matches wins. A page headed "Gecorrigeerde
# telresultaten" goes on with the toegelaten kiezers.
FALLBACK_TITLES = [
    ("Ondertekening", PageContent.SIGNATURES),
    ("Gecorrigeerde telresultaten", PageContent.ADMITTED_VOTERS),
    ("Onderzoek naar telresultaten", PageContent.INVESTIGATION),
    ("Verschillen met telresultaten stembureau", PageContent.INVESTIGATION),
    ("Verslag van de zitting", PageContent.SESSION_REPORT),
]


def title_pattern(key: str) -> regex.Pattern:
    """OCR misreads headings heavily, so a title may have one misread letter in five; short keys are stricter, as
    they would match body text."""
    errors = len(key) // 5 if len(key) >= 12 else len(key) // 8
    return regex.compile(f"(?e)(?:{key}){{e<={errors}}}")


HEADING_KEYS = [(content, title_pattern(letters_only(title))) for title, content in HEADING_TITLES]
FALLBACK_KEYS = [(content, title_pattern(letters_only(title))) for title, content in FALLBACK_TITLES]
# A list heading starts a line: "Lijst 1 - CDA", "Vervolg lijst 1 PVV", "tijst 1 Ons Belong". The "E.1 Totaal lijst 1"
# lines of the votes cast do not. The first group is "vervolg" of a continued list; OCR may leave the number, the
# second group, unreadable ("Lijst & CDA").
LIST_HEADING_RE = re.compile(
    rf"^\s*((?i:vervolg)\s+)?[lLtI]ijs[tl](?![A-Za-z])\s*(?:({OCR_DIGIT}{{1,2}})\b)?", re.MULTILINE
)


class Heading(NamedTuple):
    content: PageContent
    list_number: int | None = None
    has_list_heading: bool = False


@dataclass
class TocEntry:
    page: int
    content: PageContent
    list_number: int | None = None
    # The OCR text of the page header, kept for debugging.
    text: str = ""
    # Whether the list number was inferred from the neighbouring pages rather than read.
    list_number_inferred: bool = False
    # Whether a list heading was read, whether or not its number was.
    has_list_heading: bool = False


@dataclass
class TableOfContents:
    entries: list[TocEntry]

    def to_json(self) -> list[dict]:
        return [
            {"page": e.page, "content": str(e.content)}
            | ({"list_number": e.list_number} if e.list_number else {})
            | ({"list_number_inferred": True} if e.list_number_inferred else {})
            for e in self.entries
        ]


def infer_list_numbers(entries: list[TocEntry]) -> None:
    """Fill in or correct misread list numbers from the pages around them, within each run of list pages."""
    run: list[TocEntry] = []
    for entry in [*entries, None]:
        if entry is not None and entry.content in LIST_CONTENTS:
            run.append(entry)
        else:
            infer_run(run)
            run = []


def between(lower: int | None, number: int, upper: int | None) -> bool:
    return (lower is None or number > lower) and (upper is None or number < upper)


def infer_run(run: list[TocEntry]) -> None:
    """
    Infer numbers in a run of consecutive list pages, going forward.

    A list heading with no number, or one that does not fit between the lists around it, takes the one number
    between them, only when exactly one fits: numbers may skip, so a wider gap, or no list before or after, is left
    as read. A number is trusted as the list before only when it fits (or is the first) and is not above all later
    lists. A continued page takes the number of its list when that is trusted; otherwise its own number, if it fits
    between the lists around it, replaces the list's, also on the pages before it. A repeated "Lijst N" counts as a
    misread, as each later page of a list prints "Vervolg lijst N" or no heading, and the number of the next list is
    taken as read.
    """
    # The trusted number of the list before, of the list a page is in (None when untrusted), the page that opened
    # that list, and its continued pages seen while the number was untrusted.
    previous = current = owner = None
    pending: list[TocEntry] = []
    for i, entry in enumerate(run):
        read = entry.list_number
        later = [e.list_number for e in run[i + 1 :] if e.content == PageContent.CANDIDATE_VOTES and e.list_number]
        following = later[0] if later else None
        if entry.content == PageContent.CANDIDATE_VOTES_CONTINUED:
            if current is not None:
                if read != current:
                    entry.list_number, entry.list_number_inferred = current, True
            elif read is not None and between(previous, read, following):
                # The page names its list, whose own number is unreadable or untrusted.
                for page in [owner, *pending] if owner else pending:
                    if page.list_number != read:
                        page.list_number, page.list_number_inferred = read, True
                previous = current = read
            else:
                pending.append(entry)
            continue
        if not (entry.has_list_heading or read):
            # The page of the section title has no list.
            continue

        fits = read is not None and between(previous, read, following)
        number = read
        if not fits and previous is not None and following is not None and following - previous == 2:
            number = previous + 1
            entry.list_number, entry.list_number_inferred = number, True
        owner, pending = entry, []
        # Trusted: not above all later lists, and fitting, inferred or the first.
        trusted = (
            number is not None and number <= max(later, default=number) and (fits or number != read or previous is None)
        )
        current = number if trusted else None
        if trusted:
            previous = number


class PvDetermineTOC:
    def __init__(self, file: Path | NamedBytesIO, header_fraction: float = HEADER_FRACTION, model: str | None = None):
        """With a model, only the contents it has (MODEL_CONTENTS) are recognized; without one, all are."""
        if model is not None and model not in MODEL_CONTENTS:
            raise ValueError(f"Unknown model {model!r}")
        self.file = NamedBytesIO.from_path(file) if isinstance(file, Path) else file
        self.header_fraction = header_fraction
        self.allowed = MODEL_CONTENTS[model] if model else None

    def header_images(self) -> Iterator[Image.Image | None]:
        """The top part of each page, or None for a page beyond A3, which is a map or poster and not read."""
        pdf = pdfium.PdfDocument(self.file)
        try:
            # Filled-in form fields are only drawn once forms are initialized.
            pdf.init_forms()
            for page in pdf:
                width, height = page.get_size()
                if (scale := render_scale(width, height)) is None:
                    yield None
                    continue
                # Crop cuts the rest off in points, so it is never rasterized.
                crop = (0, height * (1 - self.header_fraction), 0, 0)
                yield page.render(scale=scale, grayscale=True, crop=crop).to_pil()
        finally:
            pdf.close()

    def empty_bodies(self, pages: Iterable[int]) -> set[int]:
        """The given pages (1-based) whose body holds no ink."""
        pdf = pdfium.PdfDocument(self.file)
        empty = set()
        try:
            pdf.init_forms()
            for number in pages:
                page = pdf[number - 1]
                width, height = page.get_size()
                top, bottom = BODY_BAND
                crop = (width * BODY_SIDE_MARGIN, height * (1 - bottom), width * BODY_SIDE_MARGIN, height * top)
                if self.body_is_empty(page.render(scale=BODY_DPI / 72, grayscale=True, crop=crop).to_pil()):
                    empty.add(number)
        finally:
            pdf.close()
        return empty

    @staticmethod
    def body_is_empty(image: Image.Image) -> bool:
        """Whether no horizontal strip of the body image has more ink than the limit."""
        strips = round((BODY_BAND[1] - BODY_BAND[0]) / BODY_STRIP_HEIGHT)
        mask = image.point(lambda v: 255 if v < INK_GREY_LEVEL else 0)
        # Float mode keeps the share of a strip precise; 8-bit is too coarse for 0.5%.
        shares = mask.convert("F").resize((1, strips), Image.Resampling.BOX)
        return shares.getextrema()[1] / 255 <= EMPTY_STRIP_INK_SHARE

    @staticmethod
    def identify_heading(text: str, allowed: frozenset[PageContent] | None = None) -> Heading:
        """The content a heading on the page names, the list number of a candidate votes page, and whether a list
        heading was found. Titles of contents outside `allowed` are ignored."""
        page = letters_only(text)
        # Where each title is found, with its errors. The Inhoudsopgave lists the titles of the parts, so it decides.
        found = []
        for content, pattern in HEADING_KEYS:
            if (allowed is None or content in allowed) and (match := pattern.search(page)):
                found.append((match.start(), sum(match.fuzzy_counts), content))
        if any(content == PageContent.TABLE_OF_CONTENTS for _, _, content in found):
            return Heading(PageContent.TABLE_OF_CONTENTS)

        # The first title found is the heading; later matches come from text below it.
        content = min(found)[2] if found else None
        if content in (None, PageContent.CANDIDATE_VOTES) and (match := LIST_HEADING_RE.search(text)):
            list_content = PageContent.CANDIDATE_VOTES_CONTINUED if match.group(1) else PageContent.CANDIDATE_VOTES
            if allowed is None or list_content in allowed:
                # An unreadable number leaves the list unknown rather than inherited.
                number = int(match.group(2).translate(TO_DIGIT)) if match.group(2) else 0
                return Heading(list_content, number or None, True)
        return Heading(content or PageContent.UNKNOWN)

    @staticmethod
    def identify_part(text: str, allowed: frozenset[PageContent] | None = None) -> PageContent:
        """The content a part title in the running header names, which is all a page without a heading has."""
        page = letters_only(text)
        keys = (key for key in FALLBACK_KEYS if allowed is None or key[0] in allowed)
        return next((content for content, pattern in keys if pattern.search(page)), PageContent.UNKNOWN)

    def determine(self) -> TableOfContents:
        entries: list[TocEntry] = []
        # The pages that took their content from the list before them, which may be blank back pages.
        inherited: list[int] = []
        for number, image in enumerate(self.header_images(), start=1):
            text = PvClassifier.ocr(image) if image is not None else ""
            unrestricted = self.identify_heading(text)
            heading = unrestricted
            if self.allowed is not None and unrestricted.content not in self.allowed:
                heading = self.identify_heading(text, self.allowed)
            content, list_number, has_list_heading = heading
            previous = entries[-1] if entries else None
            if content == PageContent.UNKNOWN and text.strip():
                content = self.identify_part(text, self.allowed)
                if (
                    content in VOTE_COUNT_CONTENTS | {PageContent.UNKNOWN}
                    and previous
                    and previous.content in LIST_CONTENTS
                    and (self.allowed is None or PageContent.CANDIDATE_VOTES_CONTINUED in self.allowed)
                    # A page headed by a section the model lacks is no continuation.
                    and unrestricted.content == PageContent.UNKNOWN
                ):
                    # A continuation page has no heading, and a counts part's running header does not end its list.
                    # The list number may be unknown, and is then inferred.
                    content, list_number = PageContent.CANDIDATE_VOTES_CONTINUED, previous.list_number
                    inherited.append(number)
                if content == PageContent.UNKNOWN and number == 1:
                    content = PageContent.COVER
            entries.append(TocEntry(number, content, list_number, text, has_list_heading=has_list_heading))
        # Inference runs first, so blank pages still count as continuations of their list. Checking the
        # bodies after the loop also keeps a blank page from ending the list for the pages after it.
        infer_list_numbers(entries)
        if inherited:
            empty = self.empty_bodies(inherited)
            for entry in entries:
                if entry.page in empty:
                    entry.content, entry.list_number, entry.list_number_inferred = PageContent.EMPTY_PAGE, None, False
        return TableOfContents(entries)
