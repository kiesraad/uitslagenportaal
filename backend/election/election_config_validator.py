from datetime import datetime

from election.models import ElectionCategory, TimelineDateQualifier, TimelineEvent

_REQUIRED_ELECTION_FIELDS = (
    "id",
    "label",
    "category",
    "date",
    "issue_report_opens_at",
    "issue_report_deadline",
)


def _check_iso_datetime(value, path: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{path}: expected an ISO 8601 datetime string, got {type(value).__name__}")
        return
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{path}: {value!r} is not a valid ISO 8601 datetime")
        return
    if parsed.tzinfo is not None:
        errors.append(f"{path}: {value!r} must be a naive datetime (no timezone offset)")


def _check_timeline_dates(data: dict, errors: list[str]) -> None:
    entries = data.get("timeline_dates")
    if not isinstance(entries, list):
        errors.append(f"timeline_dates: expected a list, got {type(entries).__name__}")
        return

    # Only strings can name an event; anything else is reported per entry below.
    events = {e.get("event") for e in entries if isinstance(e, dict) and isinstance(e.get("event"), str)}
    missing = TimelineEvent.required() - events
    if missing:
        errors.append(f"timeline_dates: some events are missing: {', '.join(sorted(missing))}")

    for index, entry in enumerate(entries):
        path = f"timeline_dates[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{path}: expected an object, got {type(entry).__name__}")
            continue

        if "date" in entry:
            _check_iso_datetime(entry["date"], f"{path}.date", errors)
        else:
            errors.append(f"{path}.date: required")

        for key, enum, required in [("event", TimelineEvent, True), ("qualifier", TimelineDateQualifier, False)]:
            if key not in entry and required:
                errors.append(f"{path}.{key}: required")
            elif key in entry:
                try:
                    enum(entry[key])
                except ValueError:
                    errors.append(f"{path}.{key}: is not one of {', '.join(enum.__members__.values())}")


def validate_election_config(data: dict) -> list[str]:
    """
    Validate parsed election_config JSON against the same shape election_config_importer.py expects.

    Returns a list of human-readable problems; an empty list means the importer should accept the file.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return [f"top level: expected an object, got {type(data).__name__}"]

    election_data = data.get("election")
    if not isinstance(election_data, dict):
        errors.append("election: required object is missing")
        return errors

    for field in _REQUIRED_ELECTION_FIELDS:
        if not election_data.get(field):
            errors.append(f"election.{field}: required")

    category = election_data.get("category")
    if category and category not in ElectionCategory.values:
        errors.append(f"election.category: {category!r} is not one of {', '.join(ElectionCategory.values)}")

    for field in ("date", "issue_report_opens_at", "issue_report_deadline"):
        if election_data.get(field):
            _check_iso_datetime(election_data[field], f"election.{field}", errors)

    _check_timeline_dates(data, errors)

    return errors
