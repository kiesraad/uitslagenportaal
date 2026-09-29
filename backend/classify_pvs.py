"""POC: classify processen-verbaal by model and, where possible, region, using Tesseract on the first two pages.

A model counts as identified when its code and its title are both on the page, or its title alone.

Run from backend/ (Tesseract with Dutch language data is in the dev image):
docker compose run --rm backend-scripts python classify_pvs.py [paths ...] \
    [--limit N] [--sample N] [--show-text] [--jobs N]
"""

import argparse
import os
import random
import re
import time
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
import pytesseract
import regex
from PIL import Image

PVS = Path(__file__).parent / ".data" / "PVs"

DPI = 300
# OCR of the top 40% first is fastest overall, although OSV forms, whose titles sit lower, then need a full page.
CROP_FRACTION = 0.4

# Known models; a code outside this list is taken to be misread. A bijlage is an attachment to a PV, not the PV
# itself, so it is a model of its own: "<code> Bijlage <n>".
MODELS = {
    "N 10-1": "stembureau, decentrale stemopneming",
    "N 10-2": "stembureau, centrale stemopneming",
    "N 11": "burgemeester, vaststelling aantal stemmen in gemeente (tot 2021)",
    "Na 14-1": "corrigendum stembureau, herteld door gemeentelijk stembureau",
    "Na 14-2": "corrigendum gemeentelijk stembureau",
    "Na 14-2 Bijlage 1": "corrigendum gemeentelijk stembureau, verslagen van hertelde stembureaus",
    "Na 14-2 Bijlage 2": "corrigendum gemeentelijk stembureau, correctie van uitkomsten per stembureau",
    "Na 31-1": "gemeentelijk stembureau, decentrale stemopneming",
    "Na 31-2": "gemeentelijk stembureau, centrale stemopneming",
    "Na 31-2 Bijlage 1": "gemeentelijk stembureau, verslagen van tellingen van stembureaus",
    "Na 31-2 Bijlage 2": "gemeentelijk stembureau, uitkomsten per stembureau",
    "O 7": "hoofdstembureau",
    "P 1f-1": "corrigendum hoofdstembureau",
    "P 2a": "nieuwe zitting gemeentelijk stembureau, gecorrigeerde telresultaten",
    "P 22-1": "centraal stembureau, uitslag TK, EP en PS met meer dan één kieskring",
    "P 22-2": "centraal stembureau, uitslag en zetelverdeling",
    "I 1": "centraal stembureau, onderzoek kandidatenlijsten",
    "I 4": "centraal stembureau, kandidatenlijsten en nummering",
}

# Texts that appear on one model only, as printed on the Kiesraad forms and the OSV versions of them. OSV headers such
# as "Verslag en telresultaten per lijst en kandidaat" and "Details van het stembureau" are shared by several models.
TITLES = [
    ("Proces-verbaal van een stembureau (decentrale stemopneming)", "N 10-1"),
    ("hoeveel stemmen elke lijst en elke kandidaat hebben gekregen", "N 10-1"),
    ("Proces-verbaal van een stembureau (centrale stemopneming)", "N 10-2"),
    ("hoeveel stemmen elke lijst heeft gekregen", "N 10-2"),
    ("Vaststelling aantal stemmen in gemeente", "N 11"),
    ("Corrigendum bij het proces-verbaal van een stembureau", "Na 14-1"),
    ("Verslag van telling van een door het gemeentelijk stembureau herteld stembureau", "Na 14-1"),
    ("Corrigendum bij het proces-verbaal van een gemeentelijk stembureau", "Na 14-2"),
    ("Corrigendum van een gemeentelijk stembureau", "Na 14-2"),
    ("Verslagen van tellingen van stembureaus die zijn herteld door het gemeentelijk stembureau", "Na 14-2 Bijlage 1"),
    ("Bijlage 2: Correctie van fouten in het proces-verbaal van het gemeentelijk stembureau", "Na 14-2 Bijlage 2"),
    ("hoeveel stemmen elke lijst en elke kandidaat kreeg", "Na 31-1"),
    ("Proces-verbaal van een gemeentelijk stembureau (centrale stemopneming)", "Na 31-2"),
    ("gemeentelijk stembureau in een gemeente waar een centrale stemopneming wordt verricht", "Na 31-2"),
    ("Het gemeentelijk stembureau telt de stemmen per kandidaat", "Na 31-2"),
    ("Bijlage 1 - verslag telling stembureau", "Na 31-2 Bijlage 1"),
    ("Verslagen van tellingen van stembureaus", "Na 31-2 Bijlage 1"),
    ("Bijlage 2: uitkomsten per stembureau", "Na 31-2 Bijlage 2"),
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


def render_page(path: Path, index: int) -> Image.Image | None:
    with pymupdf.open(path) as doc:
        if index >= doc.page_count:
            return None
        pix = doc[index].get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples)


def ocr(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang="nld", config="--psm 6")


def rotate_upright(image: Image.Image) -> Image.Image | None:
    """Rotate a scan upright using Tesseract's orientation detection, or None if it is upright or unknown."""
    try:
        angle = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)["rotate"]
    except pytesseract.TesseractError:
        return None
    # OSD gives the clockwise correction; PIL rotates anticlockwise.
    return image.rotate(-angle, expand=True) if angle else None


@dataclass
class Result:
    model: str | None
    basis: str
    codes: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    found_by: str = ""
    text: str = ""


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


@dataclass
class TitleMatch:
    model: str
    errors: int
    length: int
    start: int
    end: int

    def beaten_by(self, other: "TitleMatch") -> bool:
        """Whether another title found at the same place fits better, or equally well and is longer."""
        if other is self or other.end <= self.start or self.end <= other.start:
            return False
        return (other.errors, -other.length) < (self.errors, -self.length)


def find_titles(text: str) -> list[str]:
    """Return the models whose titles are on the page."""
    page = letters_only(text)
    found = []
    for key, pattern, model in TITLE_KEYS:
        if (start := page.find(key)) >= 0:
            found.append(TitleMatch(model, 0, len(key), start, start + len(key)))
        elif match := pattern.search(page):
            found.append(TitleMatch(model, sum(match.fuzzy_counts), len(key), *match.span()))
    # Similar titles match at the same place: "… stembureaus" inside "… stembureaus die zijn herteld", or "centrale"
    # with two errors inside "decentrale". Only the best fit there counts.
    found = [m for m in found if not any(m.beaten_by(other) for other in found)]
    # A misread match for another PV than an exact one is text that merely resembles a title, like "bijlage 2 … (de
    # uitkomsten per stembureau)" in the instructions of a Na 14-2 bijlage 2.
    exact = {pv_code(m.model) for m in found if not m.errors}
    return sorted({m.model for m in found if not m.errors or not exact or pv_code(m.model) in exact})


def identify(text: str) -> Result:
    """Decide the model from the codes and titles on the page, preferring no model over a doubtful one."""
    codes, titles = find_codes(text), find_titles(text)
    known = [code for code in codes if code in PV_CODES]
    # A bijlage page often repeats its PV's title; the bijlage title then decides.
    titles = [title for title in titles if not any(other != title and pv_code(other) == title for other in titles)]
    # Titles of different models on one page contradict each other, so a model is only decided by a single one.
    if len(titles) > 1:
        return Result(None, "conflict", codes, titles)
    if titles:
        if pv_code(titles[0]) in known:
            return Result(titles[0], "code+title", codes, titles)
        if known:
            return Result(None, "conflict", codes, titles)
        return Result(titles[0], "title", codes, titles)
    if known:
        return Result(known[0], "code", codes, titles)
    return Result(None, "unknown" if codes else "none", codes, titles)


def find_region(text: str) -> dict[str, str]:
    region = {}
    if match := GEMEENTE_RE.search(text):
        region["gemeente"] = match.group(1).zfill(4)
    if match := STEMBUREAU_RE.search(text):
        region["stembureau"] = match.group(1)
    if match := KIESKRING_RE.search(text):
        region["kieskring"] = match.group(1)
    return region


def find_election(text: str, path: Path) -> tuple[str, str]:
    """Return the election, e.g. "GR2026", and where it came from: the PDF text, the file name, or neither."""
    flat = " ".join(text.split())
    for match in ELECTION_TYPE_RE.finditer(flat):
        if year := ELECTION_YEAR_RE.search(flat, match.end(), match.end() + ELECTION_YEAR_WINDOW):
            return f"{match.lastgroup}{year.group(1)}", "pdf"
    if match := ELECTION_CODE_TEXT_RE.search(flat):
        return f"{match.group(1)}20{match.group(2)}", "pdf"
    # Bijlagen don't name the election on their first page.
    if match := ELECTION_CODE_NAME_RE.search(path.stem):
        return f"{match.group(1).upper()}20{match.group(2)}", "name"
    return "", ""


def ocr_passes(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (pass, text) from cheapest to most expensive; later passes only run when asked for."""
    page = render_page(path, 0)
    yield "crop", ocr(page.crop((0, 0, page.width, int(page.height * CROP_FRACTION))))
    full = ocr(page)
    yield "full", full
    if upright := rotate_upright(page):
        yield "rotated", ocr(upright)
    # Some GSB bijlagen have only a title on page 1 and the model on page 2; page 1 keeps the bijlage and region.
    if second := render_page(path, 1):
        yield "page2", full + "\n" + ocr(second)


def classify(path: Path) -> Result:
    """Run OCR passes until the model is identified; otherwise return the best-supported result of all passes."""
    best = None
    for found_by, text in ocr_passes(path):
        result = identify(text)
        result.found_by, result.text = found_by, text
        if best is None or BASES.index(result.basis) < BASES.index(best.basis):
            best = result
        if result.basis in ("code+title", "title"):
            break
    return best


def classify_timed(path: Path) -> tuple[Result | None, str | None, float]:
    """Classify one file, also in a worker process: the result or the error, and the seconds it took."""
    start = time.perf_counter()
    try:
        result, error = classify(path), None
    except Exception as exc:
        result, error = None, repr(exc)
    return result, error, time.perf_counter() - start


def collect_pdfs(paths: list[Path]) -> list[Path]:
    pdfs = []
    for path in paths:
        if path.is_dir():
            pdfs.extend(p for p in sorted(path.rglob("*.pdf")) if "_tools" not in p.parts)
        else:
            pdfs.append(path)
    return pdfs


def display_name(path: Path) -> str:
    path, root = path.resolve(), PVS.resolve()
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, default=[PVS])
    parser.add_argument("--limit", type=int, default=25, help="classify at most N files; 0 for all (default 25)")
    parser.add_argument("--sample", type=int, help="classify N randomly chosen files instead of the first ones")
    parser.add_argument("--show-text", action="store_true", help="print the OCR text of files not identified")
    parser.add_argument(
        "--jobs", type=int, default=1, help="classify N files at a time in worker processes (default 1)"
    )
    args = parser.parse_args()

    pdfs = collect_pdfs(args.paths)
    if args.sample:
        pdfs = random.Random(0).sample(pdfs, min(args.sample, len(pdfs)))
    elif args.limit:
        pdfs = pdfs[: args.limit]

    # Rows are printed as each file is done, so the columns have fixed widths and the file name goes last.
    # "model" is the verdict; "code" and "title" show what OCR found on the page.
    # "election" comes from the PDF, or from the file name when "from" says so.
    row = "{:<18} {:<10} {:<8} {:<17} {:<8} {:<4} {:<8} {:<10} {:<9} {:<7} {:>6}  {}"
    header = row.format(
        "model",
        "basis",
        "code",
        "title",
        "election",
        "from",
        "gemeente",
        "stembureau",
        "kieskring",
        "pass",
        "time",
        "file",
    )
    print(header)
    print("-" * len(header))

    models, bases, elections = Counter(), Counter(), Counter()
    if args.jobs > 1:
        # Tesseract's own threads compete with the workers; one each is about 1.6x faster with 4 jobs.
        os.environ["OMP_THREAD_LIMIT"] = "1"
    # Results come back in input order, so a slow file holds back the rows after it.
    with ProcessPoolExecutor(args.jobs) if args.jobs > 1 else nullcontext() as pool:
        outcomes = pool.map(classify_timed, pdfs) if pool else map(classify_timed, pdfs)
        for path, (result, error, seconds) in zip(pdfs, outcomes):
            if error:
                print(
                    row.format(
                        "error", "", "", "", "", "", "", "", "", "", f"{seconds:.1f}s", f"{display_name(path)}  {error}"
                    )
                )
                models["error"] += 1
                continue

            # A model read from its code alone is shown with a question mark.
            model = f"{result.model}?" if result.basis == "code" else result.model or "-"
            region = find_region(result.text)
            election, election_from = find_election(result.text, path)
            print(
                row.format(
                    model,
                    result.basis,
                    result.codes[0] if result.codes else "",
                    "/".join(result.titles),
                    election or "-",
                    election_from,
                    region.get("gemeente", ""),
                    region.get("stembureau", ""),
                    region.get("kieskring", ""),
                    result.found_by,
                    f"{seconds:.1f}s",
                    display_name(path),
                )
            )
            if result.basis not in ("code+title", "title") and args.show_text:
                print("    " + " ".join(result.text.split())[:300])
            models[model] += 1
            bases[result.basis] += 1
            elections[f"{election or '-'} {election_from}".strip()] += 1

    summary = "{:>5}  {:<18} {}"
    print()
    print(summary.format("count", "model", "description"))
    for model, count in models.most_common():
        print(summary.format(count, model, MODELS.get(model.rstrip("?"), "")))
    print()
    print(summary.format("count", "basis", ""))
    for basis in BASES:
        if bases[basis]:
            print(summary.format(bases[basis], basis, ""))
    print()
    print(summary.format("count", "election", ""))
    for election, count in sorted(elections.items()):
        print(summary.format(count, election, ""))


if __name__ == "__main__":
    main()
