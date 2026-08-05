from django.core.management.base import BaseCommand

from eml_import.utils.github_eml_importer import GithubEmlImporter


class Command(BaseCommand):
    help = "Import the next batch of commits from GitHub."

    def handle(self, *args, **options):
        file_cnt = GithubEmlImporter().run()
        self.stdout.write(self.style.SUCCESS(f"Processed {file_cnt} file(s)."))
