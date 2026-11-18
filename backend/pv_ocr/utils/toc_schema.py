"""The table of contents of a PV as stored on ElectionDocument.toc.

Kept free of the OCR dependencies, as the election models import it.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from django.db import models

# Raise when the stored shape changes; from_json rejects other versions.
TOC_VERSION = 1


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


@dataclass
class TocEntry:
    page: int
    content: PageContent
    list_number: int | None = None
    # The OCR text of the page header, kept for debugging; not stored.
    text: str = ""
    # Whether the list number was inferred from the neighbouring pages rather than read.
    list_number_inferred: bool = False
    # Whether a list heading was read, whether or not its number was; not stored.
    has_list_heading: bool = False


@dataclass
class TableOfContents:
    entries: list[TocEntry]

    def to_json(self) -> dict[str, Any]:
        return {
            "version": TOC_VERSION,
            "entries": [
                {"page": e.page, "content": str(e.content)}
                | ({"list_number": e.list_number} if e.list_number else {})
                | ({"list_number_inferred": True} if e.list_number_inferred else {})
                for e in self.entries
            ],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "TableOfContents":
        """Raises ValueError on another version or an unknown page content."""
        if data.get("version") != TOC_VERSION:
            raise ValueError(f"Unsupported table of contents version {data.get('version')!r}")
        return cls(
            [
                TocEntry(
                    page=entry["page"],
                    content=PageContent(entry["content"]),
                    list_number=entry.get("list_number"),
                    list_number_inferred=entry.get("list_number_inferred", False),
                )
                for entry in data["entries"]
            ]
        )


class TableOfContentsField(models.JSONField):
    """A JSONField that holds a TableOfContents. Lookup values other than a TableOfContents pass through as JSON."""

    def from_db_value(self, value, expression, connection):
        value = super().from_db_value(value, expression, connection)
        return None if value is None else TableOfContents.from_json(value)

    def get_prep_value(self, value):
        if isinstance(value, TableOfContents):
            value = value.to_json()
        return super().get_prep_value(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return value.to_json() if isinstance(value, TableOfContents) else value
