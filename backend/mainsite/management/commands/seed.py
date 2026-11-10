from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from election.models import ElectionConfig, TimelineDate

TIMELINE_DATES = [
    {"event": "csb_result_publish", "date": "2026-09-26T16:00:00"},
    {"event": "csb_check", "date": "2026-09-26T09:00:00"},
    {"event": "electoral_district_vote_count", "date": "2026-09-25T09:00:00"},
    {"event": "municipality_vote_count", "date": "2026-09-24T09:00:00"},
    {"event": "sb_vote_count", "date": "2026-09-23T20:00:00"},
]

WS2023_ELECTION_SEED = {
    "election": {
        "id": "AB2023",
        "label": "Waterschapsverkiezingen 2023",
        "category": "WS",
        "date": "2026-09-23T08:00:00",
        "issue_report_opens_at": "2026-09-23T10:00:00",
        "issue_report_deadline": "2026-09-27T17:00:00",
        "report_error_url": "https://www.kiesraad.nl/service/contact",
        "counting_info_url": "https://www.kiesraad.nl/verkiezingen",
        "voting_url": "https://www.kiesraad.nl/actueel/agenda",
        "gh_counting_results_branch": "auto-ab2023-partial-tel",
        "gh_exchange_branch": "auto-ab2023-uit",
    },
    "timeline_dates": TIMELINE_DATES,
}

PS2023_ELECTION_SEED = {
    "election": {
        "id": "PS2023",
        "label": "Provinciale Statenverkiezingen 2023",
        "category": "PS",
        "date": "2026-09-23T08:00:00",
        "issue_report_opens_at": "2026-09-23T10:00:00",
        "issue_report_deadline": "2026-09-27T17:00:00",
        "report_error_url": "https://www.kiesraad.nl/service/contact",
        "counting_info_url": "https://www.kiesraad.nl/verkiezingen",
        "voting_url": "https://www.kiesraad.nl/actueel/agenda",
        "gh_counting_results_branch": "auto-ps2023-partial-tel",
        "gh_exchange_branch": "auto-ps2023-uit",
    },
    "timeline_dates": TIMELINE_DATES,
}

GR2026_ELECTION_SEED = {
    "election": {
        "id": "GR2026",
        "label": "Gemeenteraadsverkiezingen 2026",
        "category": "GR",
        "date": "2026-09-12T10:00:00",
        "issue_report_opens_at": "2026-08-18T11:00:00",
        "issue_report_deadline": "2026-09-12T10:00:00",
        "gh_counting_results_branch": "auto-tk2026-tel",
        "gh_exchange_branch": "auto-tk2026-uit",
    },
    "timeline_dates": TIMELINE_DATES,
}


TK2025_ELECTION_SEED = {
    "election": {
        "id": "TK2025",
        "label": "Tweede Kamer Verkiezingen 2025",
        "category": "TK",
        "date": "2026-09-12T10:00:00",
        "issue_report_opens_at": "2026-08-18T11:00:00",
        "issue_report_deadline": "2026-09-12T10:00:00",
        "gh_counting_results_branch": "auto-tk2025-tel",
        "gh_exchange_branch": "auto-tk2025-uit",
    },
    "timeline_dates": TIMELINE_DATES,
}
EP2024_ELECTION_SEED = {
    "election": {
        "id": "EP2024",
        "label": "Europees Parlementsverkiezing 2024",
        "category": "EP",
        "date": "2026-09-12T10:00:00",
        "issue_report_opens_at": "2026-08-18T11:00:00",
        "issue_report_deadline": "2026-09-12T10:00:00",
        "gh_counting_results_branch": "auto-ep2024-tel",
        "gh_exchange_branch": "auto-ep2024-uit",
    },
    "timeline_dates": TIMELINE_DATES,
}


ELECTION_SEED = [
    WS2023_ELECTION_SEED,
    PS2023_ELECTION_SEED,
    GR2026_ELECTION_SEED,
    TK2025_ELECTION_SEED,
    EP2024_ELECTION_SEED,
]


class Command(BaseCommand):
    help = "Seed the database with fixture data."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_election(ELECTION_SEED)

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    def _seed_election(self, data):
        for item in data:
            election_data = item["election"]
            election_config = ElectionConfig.objects.create(
                identifier=election_data["id"],
                category=election_data["category"],
                label=election_data["label"],
                date=timezone.make_aware(
                    datetime.fromisoformat(
                        election_data["date"],
                    )
                ),
                issue_report_opens_at=timezone.make_aware(
                    datetime.fromisoformat(
                        election_data["issue_report_opens_at"],
                    )
                ),
                issue_report_deadline=timezone.make_aware(
                    datetime.fromisoformat(
                        election_data["issue_report_deadline"],
                    )
                ),
                report_error_url=election_data.get("report_error_url", ""),
                counting_info_url=election_data.get("counting_info_url", ""),
                voting_url=election_data.get("voting_url", ""),
                gh_counting_results_branch=election_data.get("gh_counting_results_branch"),
                gh_exchange_branch=election_data.get("gh_exchange_branch"),
            )
            for date_data in item.get("timeline_dates", []):
                TimelineDate.objects.create(
                    election_config=election_config,
                    event=date_data["event"],
                    date=timezone.make_aware(datetime.fromisoformat(date_data["date"])),
                )
            self.stdout.write("Elections seeded")
