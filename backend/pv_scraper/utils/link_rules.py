"""Rules for which links on an authority's website to follow and which documents may be PVs."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Files that are certainly no PV; whether any other link is a file shows from its response.
NON_PDF_RE = re.compile(r"\.(csv|xml|zip|docx?|xlsx?|odt|ods|jpe?g|png|gif|svg|mp4|eml)($|\?)", re.IGNORECASE)
# Model numbers: N 10-1/N 10-2 (stembureau), Na 14-2 (centrale stemopneming), Na 31-1/Na 31-2 (gemeentelijk
# stembureau), P 22 (centraal stembureau).
PV_STRONG_RE = re.compile(
    r"proces[\s_-]*verba|processen[\s_-]*verbaal|(^|[\s_-])pvs?([\s_.-]|$)|\bna[\s_-]?(14|31)|\bn[\s_-]?10|\bn[\s_-]?11\b|"
    r"\bp[\s_-]?22|\bo[\s_-]?3\b|\bnu[\s_-]?31",
    re.IGNORECASE,
)
# "telling" must start a word: "garantstelling" and "vaststelling" are not counts.
PV_WEAK_RE = re.compile(r"stembureau|\btelling|uitkomst|uitslag|\bgsb\b|\bcsb\b|\bhsb\b", re.IGNORECASE)
NOT_PV_RE = re.compile(
    r"controle[\s_-]*protocol|controletelling|ondersteuningsverklaring|instemmingsverklaring|garantstelling|"
    r"betalingsbewijs|waarborgsom|"
    r"kandidatenlijst|benoem|aanwijzing|instructie|handleiding|vacature|stempas|kiezerspas|"
    r"volmacht|oproep|aansluit|kennisgeving|bezwaar|folder|flyer|toegankelijk|adressen|locaties|presentatie",
    re.IGNORECASE,
)
# Any election, of any year; which one a document belongs to is left to the OCR classification. Abbreviations such as
# "gr26" and "tk2025" are often glued to underscores in file names.
ELECTION_RE = re.compile(
    r"verkiezing|gemeenteraad|tweede[\s_-]*kamer|provinciale[\s_-]*staten|waterschap|europees[\s_-]*parlement|"
    r"referendum|kieskring|(?<![a-z])(gr|tk|ps|ws|ab|ep)[\s_-]?(20)?\d\d(?!\d)",
    re.IGNORECASE,
)
# A page about elections or their results; not "gemeenteraad" alone, which also names the council's own pages.
ELECTION_PAGE_RE = re.compile(r"verkiezing|uitslag|stembureau|proces[\s_-]*verba", re.IGNORECASE)
# A year, written out ("2019") or as part of an election code ("tk23", "gr_22"); not a postcode ("2011 RD").
YEAR_RE = re.compile(
    r"(?<!\d)(20\d\d)(?!\d|\s?(?-i:[A-Z]{2})\b)|(?<![a-z])(?:gr|tk|ps|ws|ab|ep)[\s_-]?(\d\d)(?!\d)", re.IGNORECASE
)
# "documenten" only as a whole path segment or at the start of the link text: "reisdocumenten" and
# "uittreksels-en-documenten" lead into passport pages.
FOLLOW_RE = re.compile(
    r"verkiezing|uitslag|proces|verbaal|stembureau|\btelling|/documenten(/|\s|$)|^\S+\s+documenten|publicatie|/files/",
    re.IGNORECASE,
)
# Search, filter and account pages multiply endlessly and never hold the documents themselves; nor do the
# translated copies of a page (language prefixes, and slugs percent-encoded from Cyrillic or Arabic script).
NO_FOLLOW_RE = re.compile(
    r"/search/|/query/|/filters/|/zoeken|/zoekresultaten|/feedback|/blog/|/tag/|/log-?in|/inloggen|/registreren|"
    r"/aanmelden|/user/|"
    r"^https?://[^/]+/(en|de|fr|pl|tr|uk|ua|ar|es|it|pt|ro|bg|ru|zh)(/|$)|%d[0-9a-f]%[89ab][0-9a-f]",
    re.IGNORECASE,
)
# A URL path that names a file rather than a page, such as a PDF on a CDN.
FILE_PATH_RE = re.compile(r"\.(?!html?$|php$|aspx?$|jsp$)[a-z0-9]{2,4}$", re.IGNORECASE)
# Pleio file folders nest per election and per municipality; descending into one should not use up the depth.
FREE_FOLLOW_RE = re.compile(r"pleio\.nl/.*/files/[0-9a-f-]{36}$", re.IGNORECASE)
PLEIO_VIEW_RE = re.compile(r"^(https://[^/]*pleio\.nl)/files/view/", re.IGNORECASE)


def host(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .") or "unnamed"


def is_pv(context: str, file_context: str) -> tuple[bool, str]:
    """Whether a document may be a PV of any election, and if not, the reason to record."""
    # A PV folder on the site can hold other documents, so exclusions in the file's own name or text win.
    if NOT_PV_RE.search(file_context) and not PV_STRONG_RE.search(file_context):
        return False, "excluded"
    if PV_STRONG_RE.search(context):
        return True, ""
    weak = PV_WEAK_RE.search(context) or ELECTION_RE.search(context)
    if weak and not NOT_PV_RE.search(context):
        return True, ""
    return False, "excluded" if weak else "no-pv-signal"


def newest_year(text: str) -> int | None:
    """The latest year mentioned in a text, if any."""
    return max((int(year or f"20{short}") for year, short in YEAR_RE.findall(text)), default=None)


def is_results_context(context: str) -> bool:
    """A page or link about the counts themselves, rather than about the election in general."""
    return bool(PV_STRONG_RE.search(context) or (PV_WEAK_RE.search(context) and ELECTION_RE.search(context)))


def filename_for(url: str, headers: dict, text: str) -> str:
    disposition = headers.get("content-disposition", "")
    match = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", disposition, re.IGNORECASE) or re.search(
        r'filename="?([^";]+)"?', disposition, re.IGNORECASE
    )
    if match:
        name = unquote(match.group(1).strip())
    else:
        name = unquote(Path(urlsplit(url).path).name)
        if not name or "." not in name:
            name = text or name
    name = safe_name(name)[:150]
    return name if name.lower().endswith(".pdf") else name + ".pdf"
