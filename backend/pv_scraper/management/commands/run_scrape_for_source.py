
from django.core.management.base import BaseCommand

from pv_scraper.tasks import run_scrape_for_source


class Command(BaseCommand):
    help = "Run the run_scrape_for_source() task for the given ScrapeSource IDs"

    def add_arguments(self, parser):
        parser.add_argument("ids", nargs="*", type=int)

    def handle(self, *args, **options):
        for source_id in options["ids"]:
            self.stdout.write(f"Running task for ScraperSource id={source_id}...")
            run_scrape_for_source(source_id)
            self.stdout.write(f"Task for ScraperSource id={source_id} finished")
