"""Read vote totals out of an EML 510 file, the same way the importer sees them."""

from dataclasses import dataclass
from pathlib import Path

from pyeml_bindings import Eml230, Eml510
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.handlers import XmlEventHandler

# Same string the 230b importer uses when RegisteredName is empty.
BLANCO_PARTY_REGISTERED_NAME = "Blanco Lijst"

# Same parser the importer uses (stdlib ElementTree, fail on unknown properties).
_PARSER = XmlParser(ParserConfig(fail_on_unknown_properties=True), handler=XmlEventHandler)


@dataclass(frozen=True)
class PartyCount:
    list_number: int
    name: str
    votes: int


@dataclass(frozen=True)
class CandidateCount:
    position: int
    label: str
    votes: int


def format_nl(value: int) -> str:
    """Match the frontend's nl-NL integer grouping (1.779, not 1,779)."""
    return f"{value:,}".replace(",", ".")


def load_510(path: Path) -> Eml510:
    return _PARSER.from_path(path, Eml510)


def _as_list(value):
    return value if isinstance(value, list) else [value]


def _contest(eml: Eml510):
    return _as_list(eml.count.election.contests.contest)[0]


def _party_name(affiliation) -> str:
    name = affiliation.registered_name
    if name:
        return name
    return f"{BLANCO_PARTY_REGISTERED_NAME} {int(affiliation.id)}"


def _party_counts(selections) -> list[PartyCount]:
    parties = []
    for selection in selections:
        affiliation = selection.affiliation_identifier
        if affiliation is None:
            continue
        parties.append(PartyCount(int(affiliation.id), _party_name(affiliation), selection.valid_votes))
    return parties


def _candidate_counts(selections, list_number: int, labels: dict[int, str]) -> list[CandidateCount]:
    current_list: int | None = None
    candidates = []
    for selection in selections:
        if selection.affiliation_identifier is not None:
            current_list = int(selection.affiliation_identifier.id)
            continue
        if current_list != list_number or selection.candidate is None:
            continue
        position = int(selection.candidate.candidate_identifier.id)
        candidates.append(CandidateCount(position, labels[position], selection.valid_votes))
    return candidates


def total_party_counts(path: Path) -> list[PartyCount]:
    return _party_counts(_contest(load_510(path)).total_votes.selection)


def reporting_unit_party_counts(path: Path, unit_name: str) -> list[PartyCount]:
    for unit in _as_list(_contest(load_510(path)).reporting_unit_votes):
        if unit_name in (unit.reporting_unit_identifier.value or ""):
            return _party_counts(unit.selection)
    raise ValueError(f"No reporting unit whose name contains {unit_name!r} in {path}")


def total_counted(path: Path) -> int:
    return _contest(load_510(path)).total_votes.total_counted


def rejected_votes(path: Path, reason: str) -> int:
    for rejected in _contest(load_510(path)).total_votes.rejected_votes:
        if rejected.reason_code.value == reason:
            return rejected.value
    raise ValueError(f"No rejected-votes reason {reason!r} in {path}")


def candidate_labels(path_230b: Path, list_number: int) -> dict[int, str]:
    """Frontend `formatCandidateName` for one list in a 230b."""
    eml = _PARSER.from_path(path_230b, Eml230)
    contest = _as_list(eml.candidate_list.election.contest)[0]
    labels = {}
    for affiliation in contest.affiliation:
        if int(affiliation.affiliation_identifier.id) != list_number:
            continue
        for candidate in affiliation.candidate:
            person = candidate.candidate_full_name.person_name
            last_name = person.last_name.content[0]
            initials = person.name_line.content[0] if person.name_line else ""
            first_name = person.first_name.content[0] if person.first_name else None
            name_prefix = person.name_prefix.content[0] if person.name_prefix else None
            surname = " ".join(part for part in (name_prefix, last_name) if part)
            if first_name:
                labels[int(candidate.candidate_identifier.id)] = (
                    f"{surname}, {initials or first_name[0]} ({first_name})"
                )
            elif initials:
                labels[int(candidate.candidate_identifier.id)] = f"{surname}, {initials}"
            else:
                labels[int(candidate.candidate_identifier.id)] = surname
    return labels


def total_candidate_counts(path_510: Path, path_230b: Path, list_number: int) -> list[CandidateCount]:
    labels = candidate_labels(path_230b, list_number)
    return _candidate_counts(_contest(load_510(path_510)).total_votes.selection, list_number, labels)
