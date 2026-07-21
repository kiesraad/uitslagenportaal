from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from election.models import ElectionConfig, TimelineEntry, TimelineVariant

WS2023_ELECTION_SEED = [
    {
        "election": {
            "id": "AB2023",
            "label": "Waterschappen 2023",
            "category": "WS",
            "date": "2023-12-15T11:00:00",
            "csb_type": "WATERSCHAP"
        },
        "timeline_entries_cso": [
            {
                "title": "De Kiesraad publiceert de uitslag",
                "date": "2026-12-15T11:00:00",
                "body": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
            },
            {
                "title": "Centraal Stembureau controleert",
                "date": "2026-12-14T10:00:00",
                "body": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "meldingen van kiezers die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
            },
            {
                "title": "Optelling per kieskring",
                "date": "2026-12-09T12:00:00",
                "body": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten in de "
                    "kieskring bij elkaar op."
                ),
            },
            {
                "title": "Optelling per gemeente",
                "date": "2026-12-09T08:00:00",
                "body": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
            },
            {
                "title": "Telling in de stembureaus",
                "date": "2026-12-08T21:00:00",
                "body": (
                    "Op de avond van de stemming tellen de stembureaus alleen de stemmen per lijst. Het GSB "
                    "telt de volgende dag de stemmen per lijst en per kandidaat. Dit wordt ook wel ‘centraal tellen’ "
                    "genoemd. **Het is dus nog niet de officiële uitslag van de Kiesraad.**"
                ),
            },
        ],
        "timeline_entries_dso": [
            {
                "title": "De Kiesraad publiceert de uitslag",
                "date": "2023-12-15T11:00:00",
                "body": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
            },
            {
                "title": "Centraal Stembureau controleert",
                "date": "2026-12-14T10:00:00",
                "body": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "meldingen van kiezers die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
            },
            {
                "title": "Optelling per kieskring",
                "date": "2026-12-09T12:00:00",
                "body": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten in de "
                    "kieskring bij elkaar op."
                ),
            },
            {
                "title": "Optelling per gemeente",
                "date": "2026-12-09T08:00:00",
                "body": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
            },
            {
                "title": "Telling in de stembureaus",
                "date": "2026-12-08T21:00:00",
                "body": (
                    "Op de avond van de stemming telt het stembureau de stemmen per lijst én per kandidaat. "
                    "Het GSB controleert de volgende dag de processen-verbaal van de stembureaus. Bij (vermoedelijke) "
                    "fouten worden de stemmen van dat stembureau geheel of gedeeltelijk opnieuw geteld. **Het is dus "
                    "nog niet de officiële uitslag van de Kiesraad.**"
                ),
            },
        ],
        "timeline_entries_default": [
            {
                "title": "De Kiesraad publiceert de uitslag",
                "date": "2023-12-15T11:00:00",
                "body": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
            },
            {
                "title": "Centraal Stembureau controleert",
                "date": "2026-12-14T10:00:00",
                "body": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "meldingen van kiezers die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
            },
            {
                "title": "Optelling per kieskring",
                "date": "2026-12-09T12:00:00",
                "body": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten in de "
                    "kieskring bij elkaar op."
                ),
            },
            {
                "title": "Optelling per gemeente",
                "date": "2026-12-09T08:00:00",
                "body": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
            },
            {
                "title": "Telling in de stembureaus",
                "date": "2026-12-08T21:00:00",
                "body": (
                    "De stemmen worden geteld bij de stembureaus. **Het is dus "
                    "nog niet de officiële uitslag van de Kiesraad.**"
                ),
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with fixture data."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_election(WS2023_ELECTION_SEED)

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
                csb_type=election_data["csb_type"],
                date=timezone.make_aware(
                    datetime.fromisoformat(
                        election_data["date"],
                    )
                ),
            )
            for seed_key, variant in self._TIMELINE_VARIANTS.items():
                for entry_data in item.get(seed_key, []):
                    TimelineEntry.objects.create(
                        election_config=election_config,
                        variant=variant,
                        title=entry_data["title"],
                        date=timezone.make_aware(datetime.fromisoformat(entry_data["date"])),
                        body=entry_data["body"],
                    )
            self.stdout.write("Elections seeded")
