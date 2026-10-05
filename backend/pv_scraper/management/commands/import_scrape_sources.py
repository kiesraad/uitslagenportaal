import json

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pv_scraper.models import ScrapeSource

# Other keys in the file, such as website_source, only matter to the script that builds it.
IMPORTED_FIELDS = {"kind", "name", "website", "election_pages", "exclude", "cookie_banner_label", "disabled"}


def format_error(error: ValidationError) -> str:
    if hasattr(error, "error_dict"):
        return "; ".join(f"{field}: {' '.join(messages)}" for field, messages in error.message_dict.items())
    return "; ".join(error.messages)


class Command(BaseCommand):
    help = (
        "Create or update scrape sources from an authorities.json in default storage, keyed by TOOi code. "
        "Scrape state and sources missing from the file are left alone; invalid records are skipped."
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

        created = rejected = 0
        with transaction.atomic():
            for code, fields in authorities.items():
                source = ScrapeSource.objects.filter(code=code).first() or ScrapeSource(code=code)
                try:
                    if not isinstance(fields, dict):
                        raise ValidationError("Record is not an object.")
                    for field in IMPORTED_FIELDS & fields.keys():
                        setattr(source, field, fields[field])
                    source.full_clean()
                except ValidationError as error:
                    rejected += 1
                    self.stderr.write(f"Skipped {code}: {format_error(error)}")
                    continue
                created += source._state.adding
                source.save()
        updated = len(authorities) - created - rejected
        self.stdout.write(
            self.style.SUCCESS(f"{len(authorities)} sources: {created} created, {updated} updated, {rejected} rejected")
        )
