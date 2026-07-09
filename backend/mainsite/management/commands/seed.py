from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from election.models import ElectionConfig, ElectionStep


WS2023_ELECTION_SEED = [
    {
        "election": {
            "id": "AB2023",
            "label": "Waterschappen 2023",
            "category": "WS",
            "date": "2023-12-15T11:00:00"
        },
        "steps": [
            {
                "position": 1,
                "state": "pending",
                "title": "De Kiesraad publiceert de uitslag",
                "date": "2023-12-15T11:00:00",
                "body": (
                    "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
                    "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
                ),
            },
            {
                "position": 2,
                "state": "in-progress",
                "title": "Centraal Stembureau controleert",
                "date": "2023-12-14T10:00:00",
                "body": (
                    "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
                    "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
                    "[meldingen van kiezers](#) die onderzocht moeten worden? Als het nodig is, worden de "
                    "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
                    "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
                    "de landelijke uitslag."
                ),
            },
            {
                "position": 3,
                "state": "in-progress",
                "title": "Optelling per kieskring",
                "date": "2023-12-09T12:00:00",
                "body": (
                    "De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten in de "
                    "kieskring bij elkaar op."
                ),
            },
            {
                "position": 4,
                "state": "done",
                "title": "Optelling per gemeente",
                "date": "2023-12-09T08:00:00",
                "body": (
                    "De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in "
                    "de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en "
                    "deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag."
                ),
            },
            {
                "position": 5,
                "state": "done",
                "title": "Telling in de stembureaus",
                "date": "2023-12-08T21:00:00",
                "body": (
                    "Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen "
                    "hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag "
                    "die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus en "
                    "wordt gepubliceerd door media en persbureaus. **Het is dus nog niet de officiële "
                    "uitslag van de Kiesraad.**"
                ),
            },
        ],
    },
    # {
    #     "election": {
    #         "id": "ps2023",
    #         "label": "Provinciale Staten 2023",
    #         "category": "PS",
    #     },
    #     "steps": [
    #         {
    #             "position": 1,
    #             "state": "pending",
    #             "title": "De Kiesraad publiceert de uitslag",
    #             "date": "2023-12-15T11:00:00",
    #             "body": (
    #                 "In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, "
    #                 "hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen."
    #             ),
    #         },
    #         {
    #             "position": 2,
    #             "state": "in-progress",
    #             "title": "Centraal Stembureau controleert",
    #             "date": "2023-12-14T10:00:00",
    #             "body": (
    #                 "De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. "
    #                 "Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er "
    #                 "[meldingen van kiezers](#) die onderzocht moeten worden? Als het nodig is, worden de "
    #                 "resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.\n\n"
    #                 "Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot "
    #                 "de landelijke uitslag."
    #             ),
    #         },
    #     ],
    # },
]


class Command(BaseCommand):
    help = "Seed the database with fixture data."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._seed_election(WS2023_ELECTION_SEED)

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    def _seed_election(self, data):
        for item in data:
            election_data = item["election"]
            election_config = ElectionConfig.objects.create(
                identifier=election_data["id"],
                category=election_data["category"],
                label=election_data["label"],
                date=timezone.make_aware(datetime.fromisoformat(election_data["date"],))
            )
            for step_data in item["steps"]:
                ElectionStep.objects.create(
                    election_config=election_config,
                    position=step_data["position"],
                    state=step_data["state"],
                    title=step_data["title"],
                    date=timezone.make_aware(datetime.fromisoformat(step_data["date"])),
                    body=step_data["body"],
                )
            self.stdout.write(f"Elections seeded")
