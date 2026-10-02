import json

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pv_scraper.models import ScrapeSource


class Command(BaseCommand):
    help = (
        "Create or update scrape sources from an authorities.json in default storage, keyed by TOOi code. "
        "Scrape state and sources missing from the file are left alone."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="pv_scraper/authorities.json",
            help="key of the file in default storage (default pv_scraper/authorities.json)",
        )

    def handle(self, *args, **options):
        path = options["path"]
        if not default_storage.exists(path):
            raise CommandError(f"File does not exist in storage: {path}")
        with default_storage.open(path) as handle:
            authorities = json.load(handle)

        created = 0
        with transaction.atomic():
            for code, fields in authorities.items():
                # website_source only matters to the script that builds the file.
                defaults = {key: value for key, value in fields.items() if key != "website_source"}
                _, is_new = ScrapeSource.objects.update_or_create(code=code, defaults=defaults)
                created += is_new
        self.stdout.write(
            self.style.SUCCESS(f"{len(authorities)} sources: {created} created, {len(authorities) - created} updated")
        )
