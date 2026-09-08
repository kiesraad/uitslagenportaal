from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from election.models import ElectionConfig, TimelineEntry, TimelineVariant

TIMELINE_ENTRIES = {
    "timeline_entries_cso": [
        {
            "title": {
                "nl": "De Kiesraad publiceert de uitslag",
                "en": "De Kiesraad publishes the result",
            },
            "date": "2026-12-15T11:00:00",
            "body": {
                "nl": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
                "en": (
                    "The result shows how many votes each candidate received, "
                    "how many seats each party gets and which people will take a seat in the Tweede Kamer."
                ),
            },
        },
        {
            "title": {
                "nl": "Centraal Stembureau controleert",
                "en": "Central Polling Station checks",
            },
            "date": "2026-12-14T10:00:00",
            "body": {
                "nl": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "meldingen van kiezers die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
                "en": (
                    "De Kiesraad checks the count results of all kieskringen, municipalities and "
                    "polling stations. Are all documents complete? Have all votes been counted? Are there "
                    "reports from voters that need to be investigated? If necessary, the "
                    "results of certain polling stations are recounted to correct errors.\n\n"
                    "Only once everything is correct are the results of all kieskringen added together into "
                    "the national result."
                ),
            },
        },
        {
            "title": {
                "nl": "Optelling per kieskring",
                "en": "Tally per kieskring",
            },
            "date": "2026-12-09T12:00:00",
            "body": {
                "nl": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten "
                    "in de kieskring bij elkaar op."
                ),
                "en": (
                    "The 20 kieskringen in the Netherlands add together the results of "
                    "all municipalities in the kieskring."
                ),
            },
        },
        {
            "title": {
                "nl": "Optelling per gemeente",
                "en": "Tally per municipality",
            },
            "date": "2026-12-09T08:00:00",
            "body": {
                "nl": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
                "en": (
                    "The results of all polling stations are checked and transcribed from paper into "
                    "the results software and added up. The municipal polling station committee prepares a report and "
                    "shares the count results so they can be included in the national result."
                ),
            },
        },
        {
            "title": {
                "nl": "Telling in de stembureaus",
                "en": "Count at the polling stations",
            },
            "date": "2026-12-08T21:00:00",
            "body": {
                "nl": (
                    "Op de avond van de stemming tellen de stembureaus alleen de stemmen per lijst. Het GSB "
                    "telt de volgende dag de stemmen per lijst en per kandidaat. Dit wordt ook wel 'centraal tellen' "
                    "genoemd. **Het is dus nog niet de officiële uitslag van de Kiesraad.**"
                ),
                "en": (
                    "On the evening of the vote, the polling stations only count the votes per list. The GSB "
                    "counts the votes per list and per candidate the following day. "
                    "This is also known as 'central counting'. "
                    "**This is therefore not yet the official result of de Kiesraad.**"
                ),
            },
        },
    ],
    "timeline_entries_dso": [
        {
            "title": {
                "nl": "De Kiesraad publiceert de uitslag",
                "en": "De Kiesraad publishes the result",
            },
            "date": "2023-12-15T11:00:00",
            "body": {
                "nl": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
                "en": (
                    "The result shows how many votes each candidate received, "
                    "how many seats each party gets and which people will take a seat in the Tweede Kamer."
                ),
            },
        },
        {
            "title": {
                "nl": "Centraal Stembureau controleert",
                "en": "Central Polling Station checks",
            },
            "date": "2026-12-14T10:00:00",
            "body": {
                "nl": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "meldingen van kiezers die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
                "en": (
                    "De Kiesraad checks the count results of all kieskringen, municipalities and "
                    "polling stations. Are all documents complete? Have all votes been counted? Are there "
                    "reports from voters that need to be investigated? If necessary, the "
                    "results of certain polling stations are recounted to correct errors.\n\n"
                    "Only once everything is correct are the results of all kieskringen added together into "
                    "the national result."
                ),
            },
        },
        {
            "title": {
                "nl": "Optelling per kieskring",
                "en": "Tally per kieskring",
            },
            "date": "2026-12-09T12:00:00",
            "body": {
                "nl": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten "
                    "in de kieskring bij elkaar op."
                ),
                "en": (
                    "The 20 kieskringen in the Netherlands add together the results of "
                    "all municipalities in the kieskring."
                ),
            },
        },
        {
            "title": {
                "nl": "Optelling per gemeente",
                "en": "Tally per municipality",
            },
            "date": "2026-12-09T08:00:00",
            "body": {
                "nl": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
                "en": (
                    "The results of all polling stations are checked and transcribed from paper into "
                    "the results software and added up. The municipal polling station committee prepares a report and "
                    "shares the count results so they can be included in the national result."
                ),
            },
        },
        {
            "title": {
                "nl": "Telling in de stembureaus",
                "en": "Count at the polling stations",
            },
            "date": "2026-12-08T21:00:00",
            "body": {
                "nl": (
                    "Op de avond van de stemming telt het stembureau de stemmen per lijst én per kandidaat. "
                    "Het GSB controleert de volgende dag de processen-verbaal van de stembureaus. Bij (vermoedelijke) "
                    "fouten worden de stemmen van dat stembureau geheel of gedeeltelijk opnieuw geteld. **Het is dus "
                    "nog niet de officiële uitslag van de Kiesraad.**"
                ),
                "en": (
                    "On the evening of the vote, the polling station counts the votes per list and per candidate. "
                    "The GSB checks the polling stations' official reports the following day. In case of (suspected) "
                    "errors, the votes of that polling station are recounted in whole or in part. **This is therefore "
                    "not yet the official result of de Kiesraad.**"
                ),
            },
        },
    ],
    "timeline_entries_default": [
        {
            "title": {
                "nl": "De Kiesraad publiceert de uitslag",
                "en": "De Kiesraad publishes the result",
            },
            "date": "2026-12-15T11:00:00",
            "body": {
                "nl": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
                "en": (
                    "The result shows how many votes each candidate received, "
                    "how many seats each party gets and which people will take a seat in the House of Representatives."
                ),
            },
        },
        {
            "title": {
                "nl": "Centraal Stembureau controleert",
                "en": "Central Polling Station checks",
            },
            "date": "2026-12-14T10:00:00",
            "body": {
                "nl": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "meldingen van kiezers die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
                "en": (
                    "De Kiesraad checks the count results of all kieskringen, municipalities and "
                    "polling stations. Are all documents complete? Have all votes been counted? Are there "
                    "reports from voters that need to be investigated? If necessary, the "
                    "results of certain polling stations are recounted to correct errors.\n\n"
                    "Only once everything is correct are the results of all kieskringen added together into "
                    "the national result."
                ),
            },
        },
        {
            "title": {
                "nl": "Optelling per kieskring",
                "en": "Tally per constituency",
            },
            "date": "2026-12-09T12:00:00",
            "body": {
                "nl": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten "
                    "in de kieskring bij elkaar op."
                ),
                "en": (
                    "The 20 constituencies in the Netherlands add together the results of "
                    "all municipalities in the constituency."
                ),
            },
        },
        {
            "title": {
                "nl": "Optelling per gemeente",
                "en": "Tally per municipality",
            },
            "date": "2026-12-09T08:00:00",
            "body": {
                "nl": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
                "en": (
                    "The results of all polling stations are checked and transcribed from paper into "
                    "the results software and added up. The municipal polling station committee prepares a report and "
                    "shares the count results so they can be included in the national result."
                ),
            },
        },
        {
            "title": {
                "nl": "Telling in de stembureaus",
                "en": "Count at the polling stations",
            },
            "date": "2026-12-08T21:00:00",
            "body": {
                "nl": (
                    "De stemmen worden geteld bij de stembureaus. **Het is dus "
                    "nog niet de officiële uitslag van de Kiesraad.**"
                ),
                "en": (
                    "The votes are counted at the polling stations. **This is therefore "
                    "not yet the official result of de Kiesraad.**"
                ),
            },
        },
    ],
}

WS2023_ELECTION_SEED = {
    "election": {
        "id": "AB2023",
        "label": "Waterschapsverkiezingen 2023",
        "category": "WS",
        "date": "2026-08-12T10:00:00",
        "issue_report_opens_at": "2026-08-12T11:00:00",
        "issue_report_deadline": "2026-09-12T10:00:00",
        "report_error_url": "https://www.kiesraad.nl/service/contact",
        "counting_info_url": "https://www.kiesraad.nl/verkiezingen",
        "voting_url": "https://www.kiesraad.nl/actueel/agenda",
        "gh_counting_results_branch": "auto-ab2023-tel",
        "gh_exchange_branch": "auto-ab2023-uit",
    },
    **TIMELINE_ENTRIES,
}

PS2023_ELECTION_SEED = {
    "election": {
        "id": "PS2023",
        "label": "Provinciale Statenverkiezingen 2023",
        "category": "PS",
        "date": "2026-08-12T10:00:00",
        "issue_report_opens_at": "2026-08-08T11:00:00",
        "issue_report_deadline": "2026-09-12T10:00:00",
        "report_error_url": "https://www.kiesraad.nl/service/contact",
        "counting_info_url": "https://www.kiesraad.nl/verkiezingen",
        "voting_url": "https://www.kiesraad.nl/actueel/agenda",
        "gh_counting_results_branch": "auto-ps2023-tel",
        "gh_exchange_branch": "auto-ps2023-uit",
    },
    **TIMELINE_ENTRIES,
}

GR2026_ELECTION_SEED = {
    "election": {
        "id": "GR2026",
        "label": "Gemeenteraadsverkiezingen 2026",
        "category": "GR",
        "date": "2026-04-12T10:00:00",
        "issue_report_opens_at": "2026-08-18T11:00:00",
        "issue_report_deadline": "2026-09-12T10:00:00",
        "gh_counting_results_branch": "auto-tk2026-tel",
        "gh_exchange_branch": "auto-tk2026-uit",
    },
    **TIMELINE_ENTRIES,
}


TK2025_ELECTION_SEED = {
    "election": {
        "id": "TK2025",
        "label": "Tweede Kamer Verkiezingen 2025",
        "category": "TK",
        "date": "2025-04-12T10:00:00",
        "issue_report_opens_at": "2025-08-18T11:00:00",
        "issue_report_deadline": "2025-09-12T10:00:00",
        "gh_counting_results_branch": "auto-tk2025-tel",
        "gh_exchange_branch": "auto-tk2025-uit",
    },
    **TIMELINE_ENTRIES,
}


ELECTION_SEED = [WS2023_ELECTION_SEED, PS2023_ELECTION_SEED, GR2026_ELECTION_SEED, TK2025_ELECTION_SEED]


class Command(BaseCommand):
    help = "Seed the database with fixture data."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_election(ELECTION_SEED)

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    _TIMELINE_VARIANTS = {
        "timeline_entries_cso": TimelineVariant.CSO,
        "timeline_entries_dso": TimelineVariant.DSO,
        "timeline_entries_default": TimelineVariant.DEFAULT,
    }

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
            for seed_key, variant in self._TIMELINE_VARIANTS.items():
                for entry_data in item.get(seed_key, []):
                    TimelineEntry.objects.create(
                        election_config=election_config,
                        variant=variant,
                        title_nl=entry_data["title"]["nl"],
                        title_en=entry_data["title"]["en"],
                        date=timezone.make_aware(datetime.fromisoformat(entry_data["date"])),
                        body_nl=entry_data["body"]["nl"],
                        body_en=entry_data["body"]["en"],
                    )
            self.stdout.write("Elections seeded")
