"""
Render a count (510b, 510c or 510d) as the osv4-3 CSV the counting software uploads beside it.

The layout follows the uploads in the ingress repository: a header naming the election and the body
that counted, then a table per contest with a column for every reporting unit, the counts as rows, and
each party followed by its candidates. A count does not name its candidates, so their names are looked
up in the candidate lists (230b) of the same election.
"""

import codecs
import csv
import io
import re
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "e": "urn:oasis:names:tc:evs:schema:eml",
    "kr": "http://www.kiesraad.nl/extensions",
    "xnl": "urn:oasis:names:tc:ciq:xsdschema:xNL:2.0",
}

# A candidate by election, contest, party and candidate identifier. Every candidate is also filed under
# a contest of None, for a count whose contests are not the ones the lists were submitted in.
type NameKey = tuple[str | None, str | None, str | None, str | None]
type Row = tuple[str | int | None, ...]

# The contest identifier of an election without kieskringen.
NO_CONTEST = "geen"

# In an election with kieskringen the area is named with its kind: `Gemeente Vlieland`.
AREA_PREFIXES = {"510b": "Gemeente", "510c": "Kieskring"}

HEADER = ("Lijstnummer", "Aanduiding", "Volgnummer", "Naam kandidaat", "Totaal")

# The elements of a block that hold a count. The rejected and uncounted votes never share a reason
# code, so a count is known by its reason code, or by its element when it has none.
COUNT_ELEMENTS = {"Cast", "TotalCounted", "RejectedVotes", "UncountedVotes"}

# The found ballots are no count of their own, but the counted, blank and invalid ballots together.
FOUND_BALLOTS = "aangetroffen stembiljetten"
FOUND_BALLOT_PARTS = ("TotalCounted", "blanco", "ongeldig")

# The count rows in the order the CSV prints them, as (label, count). A row is only printed when the
# document carries its count: a kieskring total has no admitted voters, for one.
COUNT_ROWS = (
    ("opgeroepenen", "Cast"),
    ("geldige stempas", "geldige stempassen"),
    ("geldig volmachtbewijs", "geldige volmachtbewijzen"),
    ("geldige kiezerspas", "geldige kiezerspassen"),
    ("toegelaten kiezers", "toegelaten kiezers"),
    ("geldige stembiljetten", "TotalCounted"),
    ("blanco stembiljetten", "blanco"),
    ("ongeldige stembiljetten", "ongeldig"),
    (FOUND_BALLOTS, FOUND_BALLOTS),
    ("meer stembiljetten dan toegelaten kiezers", "meer getelde stembiljetten"),
    ("minder stembiljetten dan toegelaten kiezers", "minder getelde stembiljetten"),
    ("kiezers met stembiljet hebben niet gestemd", "meegenomen stembiljetten"),
    ("er zijn te weinig stembiljetten uitgereikt", "te weinig uitgereikte stembiljetten"),
    ("er zijn te veel stembiljetten uitgereikt", "te veel uitgereikte stembiljetten"),
    ("geen verklaring", "geen verklaring"),
    ("andere verklaring", "andere verklaring"),
)

# `Stembureau Zorgcentrum Aelsmeer (postcode: 1431 BZ)`: the CSV prints the name and postcode apart.
_UNIT_NAME_PATTERN = re.compile(r"^(?:Stembureau )?(?P<name>.*?)(?: \(postcode: (?P<postcode>[^)]*)\))?$")


def read_candidate_names(path: Path) -> dict[NameKey, str]:
    """Every candidate on the lists in a 230b, named the way the CSV prints them: `van Hilst-Dekker, C.`."""
    root = ET.parse(path).getroot()
    election_id = _identifier(root, ".//e:ElectionIdentifier")
    names: dict[NameKey, str] = {}
    for contest in root.iterfind(".//e:Contest", NS):
        contest_id = _identifier(contest, "e:ContestIdentifier")
        for affiliation in contest.iterfind("e:Affiliation", NS):
            party_id = _identifier(affiliation, "e:AffiliationIdentifier")
            for candidate in affiliation.iterfind("e:Candidate", NS):
                person = candidate.find("e:CandidateFullName/xnl:PersonName", NS)
                if person is None:
                    continue
                candidate_id = _identifier(candidate, "e:CandidateIdentifier")
                name = _person_name(person)
                names[(election_id, contest_id, party_id, candidate_id)] = name
                names.setdefault((election_id, None, party_id, candidate_id), name)
    return names


def render_csv(document: bytes, names: dict[NameKey, str]) -> bytes:
    """The osv4-3 CSV of one count, encoded the way the counting software writes it."""
    root = ET.fromstring(document)
    identifier = root.find(".//e:ElectionIdentifier", NS)
    contests = root.findall(".//e:Contest", NS)

    rows: list[Row] = [
        ("Verkiezing", None, _text(identifier, "e:ElectionName")),
        ("Datum", None, _text(identifier, "kr:ElectionDate")),
        ("Gebied", None, _area(root, contests)),
        ("Nummer", None, _identifier(root, "e:ManagingAuthority/e:AuthorityIdentifier")),
    ]
    for contest in contests:
        rows.append(())
        rows.extend(_contest_rows(contest, identifier.get("Id"), names))

    buffer = io.StringIO()
    # Every cell but an empty one is quoted, numbers included.
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_NOTNULL, lineterminator="\r\n")
    writer.writerows(rows)
    # The export ends on its last row, without a line break after it.
    return codecs.BOM_UTF8 + buffer.getvalue().removesuffix("\r\n").encode()


def _area(root: ET.Element, contests: list[ET.Element]) -> str | None:
    name = _text(root, "e:ManagingAuthority/e:AuthorityIdentifier")
    prefix = AREA_PREFIXES.get(root.get("Id"))
    has_kieskringen = any(_identifier(contest, "e:ContestIdentifier") not in (None, NO_CONTEST) for contest in contests)
    return f"{prefix} {name}" if name and prefix and has_kieskringen else name


def _contest_rows(contest: ET.Element, election_id: str | None, names: dict[NameKey, str]) -> list[Row]:
    """The table of one contest: its total in the first column, then every reporting unit."""
    total = contest.find("e:TotalVotes", NS)
    if total is None:
        return []
    units = contest.findall("e:ReportingUnitVotes", NS)
    blocks = [total, *units]
    contest_id = _identifier(contest, "e:ContestIdentifier")

    unit_names: list[str] = []
    numbers: list[str] = []
    postcodes: list[str | None] = []
    for unit in units:
        identifier = unit.find("e:ReportingUnitIdentifier", NS)
        match = _UNIT_NAME_PATTERN.match((identifier.text or "").strip())
        unit_names.append(match["name"])
        postcodes.append(match["postcode"])
        # `0358::SB1` for a polling station, `HSB9::0363` for a gemeente in a kieskring total.
        numbers.append(identifier.get("Id", "").rpartition("::")[2].removeprefix("SB"))

    rows: list[Row] = [(*HEADER, *unit_names), ("Gebiednummer", None, None, None, None, *numbers)]
    if any(postcodes):
        rows.append(("Postcode", None, None, None, None, *postcodes))

    counts = [_counts(block) for block in blocks]
    for label, count in COUNT_ROWS:
        if count in counts[0]:
            rows.append((None, label, None, None, *(block.get(count) for block in counts)))

    party_names = {
        affiliation.get("Id"): _text(affiliation, "e:RegisteredName")
        for affiliation in total.iterfind("e:Selection/e:AffiliationIdentifier", NS)
    }
    votes = [_selections(block) for block in blocks]
    for party_id, candidate_id in votes[0]:
        row_votes = [block.get((party_id, candidate_id)) for block in votes]
        if candidate_id is None:
            rows.append((party_id, party_names.get(party_id), None, None, *row_votes))
        else:
            key = (party_id, candidate_id)
            name = names.get((election_id, contest_id, *key)) or names.get((election_id, None, *key))
            rows.append((None, None, candidate_id, name, *row_votes))
    return rows


def _counts(block: ET.Element) -> dict[str, int]:
    """Every count in a block, by reason code or element name, with the found ballots added up."""
    counts: dict[str, int] = {}
    for element in block:
        tag = element.tag.rpartition("}")[2]
        if tag in COUNT_ELEMENTS:
            counts[element.get("ReasonCode", tag)] = int(element.text)
    if all(part in counts for part in FOUND_BALLOT_PARTS):
        counts[FOUND_BALLOTS] = sum(counts[part] for part in FOUND_BALLOT_PARTS)
    return counts


def _selections(block: ET.Element) -> dict[tuple[str | None, str | None], str | None]:
    """
    The valid votes of every party and candidate in a block, in document order.

    A selection naming an affiliation opens a party and holds its total; the candidate selections
    that follow belong to that party.
    """
    votes: dict[tuple[str | None, str | None], str | None] = {}
    party: str | None = None
    for selection in block.iterfind("e:Selection", NS):
        valid_votes = _text(selection, "e:ValidVotes")
        affiliation = selection.find("e:AffiliationIdentifier", NS)
        if affiliation is not None:
            party = affiliation.get("Id")
            votes[(party, None)] = valid_votes
        elif party is not None:
            votes[(party, _identifier(selection, "e:Candidate/e:CandidateIdentifier"))] = valid_votes
    return votes


def _person_name(person: ET.Element) -> str:
    last_name = " ".join(filter(None, (_text(person, "xnl:NamePrefix"), _text(person, "xnl:LastName"))))
    initials = _text(person, "xnl:NameLine[@NameType='Initials']")
    return f"{last_name}, {initials}" if initials else last_name


def _identifier(element: ET.Element, path: str) -> str | None:
    found = element.find(path, NS)
    return found.get("Id") if found is not None else None


def _text(element: ET.Element, path: str) -> str | None:
    """The trimmed text at `path`, or None when it is missing or empty, so the CSV leaves the cell unquoted."""
    found = element.find(path, NS)
    return (found.text or "").strip() or None if found is not None else None
