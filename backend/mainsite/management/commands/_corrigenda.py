"""
Generate the earlier revisions of a Telling (510b), so it can be replayed as a corrigendum.

A gemeente that corrects its count re-uploads the same document name with different votes and a
newer `kr:CreationDateTime`, which a `.data` folder cannot hold twice. The source file is the
truth, so it is the last revision; the ones before it still carry the errors it went on to fix.

An error is a miscounted polling station: a few votes moved between candidates, sometimes a few
reclassified as invalid, both mirrored into the gemeente totals so the file keeps adding up.
"""

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

EML_NS = "urn:oasis:names:tc:evs:schema:eml"
NS = {"e": EML_NS}

# At most this many corrigenda for a single Telling.
MAX_CORRIGENDA = 3

# The votes an error moves around, and the votes a candidate must hold to take part in one. Both
# amounts are capped at what the candidate actually has, because a gemeente counting for a
# neighbouring waterschap can put a handful of votes in a polling station and no more.
TRANSFERS_PER_ERROR = (1, 4)
MAX_TRANSFER_VOTES = 5
MAX_INVALID_VOTES = 3
MIN_CANDIDATE_VOTES = 2

# Tries per error before giving up on placing it, in case most polling stations are too small.
PLAN_ATTEMPTS = 10

# How often an error also reclassifies votes as invalid rather than only misattributing them.
INVALID_SHARE = 0.33

# How far apart consecutive revisions claim to have been created. Corrections are committed a
# whole round of gemeenten after the count they correct, which is hours of commit time, so an hour
# would read as too eager. Much more than this would backdate a draft to before the polls closed.
REVISION_INTERVAL = timedelta(hours=6)

# Every element holding a plain count. Matched in document order, which `ElementTree` reproduces
# exactly, so the mutated values can be substituted back into the original bytes by position.
COUNT_ELEMENTS = ("ValidVotes", "TotalCounted", "Cast", "RejectedVotes", "UncountedVotes")
_COUNT_PATTERN = re.compile(
    rb"<(" + b"|".join(tag.encode() for tag in COUNT_ELEMENTS) + rb')( ReasonCode="[^"]*")?>(\d+)</\1>'
)
_CREATION_DATE_TIME_PATTERN = re.compile(rb"(<kr:CreationDateTime>)([^<]+)(</kr:CreationDateTime>)")

# A candidate within one block: the party's list number and the candidate's identifier. The
# party's own total is keyed the same way, with no candidate.
type Key = tuple[str, str]
type Selections = dict[tuple[str, str | None], ET.Element]


@dataclass(frozen=True)
class Error:
    """One polling station's counting mistake, and the correction that later undoes it."""

    contest: int
    unit: int
    transfers: tuple[tuple[Key, Key, int], ...]
    invalid: tuple[Key, int] | None


def _rng(name: str, seed: int, purpose: str) -> random.Random:
    """
    Seed a generator from the document rather than from the run.

    Seeding on a string makes the draw reproducible across processes -- `random` hashes it with
    SHA-512, where `hash()` on a tuple would be salted per process.
    """
    return random.Random(f"{seed}:{name}:{purpose}")


@lru_cache(maxsize=None)
def _full_plan(path: Path, seed: int) -> tuple[Error, ...]:
    """
    Every error this document could carry, at most `MAX_CORRIGENDA` of them.

    Cached, because the plan is drawn once per document but read once per revision, and reading it
    means parsing the file. The errors name their polling station and candidates by index and
    identifier rather than by element, so the plan outlives the tree it was drawn from.
    """
    root = ET.fromstring(path.read_bytes())
    return tuple(_plan_errors(root, _rng(path.name, seed, "errors"), MAX_CORRIGENDA))


def draw_corrigenda(name: str, *, rate: float, seed: int) -> int:
    """
    How often a Telling named `name` is corrected: 0 to `MAX_CORRIGENDA`, each one less likely.

    Every further corrigendum needs another success at `rate`, so the counts decay geometrically
    and most gemeenten get none at all. A rate of 0 switches corrigenda off entirely.
    """
    rng = _rng(name, seed, "count")
    drawn = 0
    while drawn < MAX_CORRIGENDA and rng.random() < rate:
        drawn += 1
    return drawn


def corrigenda_for(path: Path, *, rate: float, seed: int) -> int:
    """
    The draw for this document, capped at the errors it can actually carry.

    A gemeente that counted for a neighbouring waterschap can report so few votes that there is
    nothing left to miscount. Uploading a correction that changes no count would only add empty
    commits, so such a Telling is uploaded fewer times than the draw asked for.
    """
    if rate <= 0:
        return 0
    drawn = draw_corrigenda(path.name, rate=rate, seed=seed)
    return min(drawn, len(_full_plan(path, seed))) if drawn else 0


def revision_bytes(path: Path, revision: int, corrigenda: int, *, seed: int) -> bytes:
    """
    The document as it stood at `revision`, counting from 0; `corrigenda` is the source itself.

    Revision `n` still carries the errors the plan has left after `n` corrections, so each
    revision fixes one more than the one before it and the last is the source file, untouched.
    """
    raw = path.read_bytes()
    if revision >= corrigenda:
        return raw

    root = ET.fromstring(raw)
    # The stretch of the plan this revision has not corrected yet.
    _apply_errors(root, _full_plan(path, seed)[revision:corrigenda])

    rewritten = _substitute_counts(raw, root)
    return _shift_creation_date_time(rewritten, REVISION_INTERVAL * (corrigenda - revision))


# Reading the document ---------------------------------------------------------------------


def _contests(root: ET.Element) -> list[tuple[ET.Element | None, list[ET.Element]]]:
    """Every contest as its totals block and the polling stations that make it up."""
    return [
        (contest.find("e:TotalVotes", NS), contest.findall("e:ReportingUnitVotes", NS))
        for contest in root.iterfind(".//e:Contest", NS)
    ]


def _selections(block: ET.Element) -> Selections:
    """
    The `ValidVotes` element of every selection in `block`, keyed by party and candidate.

    A selection naming an affiliation opens a party and holds that party's total; the candidate
    selections that follow belong to it, which is the same ordering `EML510bImporter` relies on.
    """
    votes: Selections = {}
    party: str | None = None
    for selection in block.iterfind("e:Selection", NS):
        affiliation = selection.find("e:AffiliationIdentifier", NS)
        valid_votes = selection.find("e:ValidVotes", NS)
        if valid_votes is None:
            continue
        if affiliation is not None:
            party = affiliation.get("Id")
            votes[(party, None)] = valid_votes
            continue
        candidate = selection.find("e:Candidate/e:CandidateIdentifier", NS)
        if party is not None and candidate is not None:
            votes[(party, candidate.get("Id"))] = valid_votes
    return votes


def _reason(block: ET.Element, tag: str, reason_code: str) -> ET.Element | None:
    """The count a block gives for one reason code, e.g. the invalid votes it rejected."""
    matches = (element for element in block.iterfind(f"e:{tag}", NS) if element.get("ReasonCode") == reason_code)
    return next(matches, None)


# Planning and applying the errors ---------------------------------------------------------


def _plan_errors(root: ET.Element, rng: random.Random, count: int) -> list[Error]:
    """
    Plan `count` counting mistakes, each confined to one polling station.

    No candidate takes part in two errors, so the errors are independent: applying any tail of the
    plan leaves a document that still balances, and no count can be driven below zero.
    """
    contests = _contests(root)
    if not contests:
        return []

    errors: list[Error] = []
    used: set[tuple[int, int, Key]] = set()

    # A polling station too small to miscount costs an attempt rather than an error, so that every
    # revision has something of its own to correct. A document made up of such stations runs out of
    # attempts and yields fewer errors than asked; `corrigenda_for` then uploads it that much less.
    for _ in range(count * PLAN_ATTEMPTS):
        if len(errors) == count:
            break
        contest_index = rng.randrange(len(contests))
        total, units = contests[contest_index]
        if total is None or not units:
            continue
        unit_index = rng.randrange(len(units))

        in_total = _selections(total)
        candidates = [
            (key, int(element.text))
            for key, element in _selections(units[unit_index]).items()
            if key[1] is not None
            and int(element.text) >= MIN_CANDIDATE_VOTES
            and key in in_total
            and (contest_index, unit_index, key) not in used
        ]
        if len(candidates) < 2:
            continue

        rng.shuffle(candidates)
        wanted = rng.randint(*TRANSFERS_PER_ERROR)
        pairs = list(zip(candidates[0::2], candidates[1::2]))[:wanted]
        # A candidate never gives away more than it holds, and takes part in one error only, so
        # its votes stay positive however much of the plan a revision still carries.
        transfers = tuple(
            (source, target, rng.randint(1, min(MAX_TRANSFER_VOTES, held))) for (source, held), (target, _) in pairs
        )
        for source, target, _ in transfers:
            used.update({(contest_index, unit_index, source), (contest_index, unit_index, target)})

        # Now and then the station also read a few of one candidate's ballots as invalid. It is
        # the candidate the first transfer took from, so what that transfer left is the ceiling.
        invalid = None
        ((_, first_held), _) = pairs[0]
        remaining = first_held - transfers[0][2]
        if (
            remaining >= 1
            and rng.random() < INVALID_SHARE
            and _reason(units[unit_index], "RejectedVotes", "ongeldig") is not None
        ):
            invalid = (transfers[0][0], rng.randint(1, min(MAX_INVALID_VOTES, remaining)))

        errors.append(Error(contest_index, unit_index, transfers, invalid))

    return errors


def _add(votes: Selections, key: Key, delta: int) -> None:
    """Move `delta` votes onto a candidate, and the same onto the party it stands for."""
    for target in (key, (key[0], None)):
        element = votes[target]
        element.text = str(int(element.text) + delta)


def _apply_errors(root: ET.Element, errors: tuple[Error, ...]) -> None:
    """Put `errors` back into the document, in the polling station and in the gemeente totals."""
    contests = _contests(root)
    for error in errors:
        total, units = contests[error.contest]
        for block in (units[error.unit], total):
            votes = _selections(block)
            for source, target, amount in error.transfers:
                _add(votes, source, -amount)
                _add(votes, target, amount)

            if error.invalid is None:
                continue
            key, amount = error.invalid
            _add(votes, key, -amount)
            counted = block.find("e:TotalCounted", NS)
            counted.text = str(int(counted.text) - amount)
            rejected = _reason(block, "RejectedVotes", "ongeldig")
            rejected.text = str(int(rejected.text) + amount)


# Writing the document ---------------------------------------------------------------------


def _substitute_counts(raw: bytes, root: ET.Element) -> bytes:
    """
    Write the mutated counts back into the original bytes, by position.

    Serialising the tree instead would drop the namespaces the root declares but never uses and
    respace every empty element, burying a corrigendum's handful of changed numbers under
    thousands of lines of noise. The counts are leaf elements, so a scan of the bytes reaches
    them in the same order as a walk of the tree.
    """
    values = iter(element.text for element in root.iter() if element.tag.rpartition("}")[2] in COUNT_ELEMENTS)

    def replace(match: re.Match[bytes]) -> bytes:
        opening_tag, _, _ = match.group(0).partition(b">")
        return b"%s>%s</%s>" % (opening_tag, next(values).encode(), match.group(1))

    rewritten = _COUNT_PATTERN.sub(replace, raw)
    assert next(values, None) is None, "Document and bytes disagree on how many counts there are"
    return rewritten


def _shift_creation_date_time(raw: bytes, delta: timedelta) -> bytes:
    """Backdate the document by `delta`, so every revision claims to precede the next."""

    def replace(match: re.Match[bytes]) -> bytes:
        original = match.group(2).decode()
        shifted = datetime.fromisoformat(original) - delta
        timespec = "milliseconds" if "." in original else "seconds"
        return match.group(1) + shifted.isoformat(timespec=timespec).encode() + match.group(3)

    return _CREATION_DATE_TIME_PATTERN.sub(replace, raw, count=1)
