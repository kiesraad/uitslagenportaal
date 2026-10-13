import pytest

from election.election_config_validator import validate_election_config
from election.models import TimelineEvent

ELECTION = {
    "id": "TK2025",
    "label": "Tweede Kamer Verkiezingen 2025",
    "category": "TK",
    "date": "2025-04-12T10:00:00",
    "issue_report_opens_at": "2025-08-18T11:00:00",
    "issue_report_deadline": "2025-09-12T10:00:00",
}


def _config(*, without: str | None = None, extra: list | None = None, **overrides) -> dict:
    """A valid config with one date per required event; `overrides` replace keys of the first one."""
    dates = [
        {"event": event.value, "date": "2025-12-15T11:00:00"}
        for event in sorted(TimelineEvent.required())
        if event != without
    ]
    dates[0] = {**dates[0], **overrides}
    return {"election": ELECTION, "timeline_dates": dates + (extra or [])}


def test_config_with_a_date_for_every_required_event_is_valid():
    assert validate_election_config(_config(date_qualifier="expected")) == []


def test_optional_events_are_accepted():
    extra = [{"event": "candidate_vote_count", "date": "2025-12-16T09:00:00"}]

    assert validate_election_config(_config(extra=extra)) == []


@pytest.mark.parametrize("timeline_dates", [None, {}, "sb_vote_count"])
def test_timeline_dates_must_be_a_list(timeline_dates):
    errors = validate_election_config({"election": ELECTION, "timeline_dates": timeline_dates})

    assert errors == [f"timeline_dates: expected a list, got {type(timeline_dates).__name__}"]


def test_missing_required_event_is_reported():
    errors = validate_election_config(_config(without=TimelineEvent.CSB_CHECK))

    assert errors == ["timeline_dates: some events are missing: csb_check"]


def test_missing_required_event_is_reported_next_to_an_optional_event():
    extra = [{"event": "candidate_vote_count", "date": "2025-12-16T09:00:00"}]

    errors = validate_election_config(_config(without=TimelineEvent.CSB_CHECK, extra=extra))

    assert errors == ["timeline_dates: some events are missing: csb_check"]


@pytest.mark.parametrize(
    ("extra", "expected_error"),
    [
        ({"event": "recount", "date": "2025-12-16T09:00:00"}, "timeline_dates[4].event: is not one of"),
        ({"date": "2025-12-16T09:00:00"}, "timeline_dates[4].event: required"),
        ({"event": "candidate_vote_count"}, "timeline_dates[4].date: required"),
        ({"event": "candidate_vote_count", "date": "16 december"}, "timeline_dates[4].date: '16 december' is not"),
        (
            {"event": "candidate_vote_count", "date": "2025-12-16T09:00:00+01:00"},
            "timeline_dates[4].date: '2025-12-16T09:00:00+01:00' must be a naive datetime",
        ),
        (
            {"event": "candidate_vote_count", "date": "2025-12-16T09:00:00", "date_qualifier": "around"},
            "timeline_dates[4].date_qualifier: is not one of",
        ),
        ("candidate_vote_count", "timeline_dates[4]: expected an object, got str"),
    ],
)
def test_malformed_timeline_date_is_reported(extra, expected_error):
    errors = validate_election_config(_config(extra=[extra]))

    assert len(errors) == 1
    assert errors[0].startswith(expected_error)
