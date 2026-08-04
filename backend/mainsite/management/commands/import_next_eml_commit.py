from django.core.management.base import BaseCommand

from eml_import.tasks.github_import import import_next_eml_commit


class Command(BaseCommand):
    help = "Import the next batch of commits from GitHub."

    def handle(self, *args, **options):
        file_cnt = import_next_eml_commit()
        self.stdout.write(self.style.SUCCESS(f"Processed {file_cnt} file(s)."))
