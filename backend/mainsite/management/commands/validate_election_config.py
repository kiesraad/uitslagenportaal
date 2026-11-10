import json

from django.core.management.base import BaseCommand, CommandError

from election.election_config_validator import validate_election_config


class Command(BaseCommand):
    help = "Validate an election_config JSON file against the shape election_config_importer.py expects."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the election_config JSON file to validate.")

    def handle(self, *args, **options):
        path = options["path"]

        try:
            with open(path) as f:
                content = f.read()
        except OSError as exc:
            raise CommandError(f"Could not read {path}: {exc}")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise CommandError(f"{path} is not valid JSON: {exc}")

        errors = validate_election_config(data)

        if not errors:
            self.stdout.write(self.style.SUCCESS(f"{path} is valid."))
            return

        self.stdout.write(self.style.WARNING(f"{path} has {len(errors)} problem(s):"))
        for error in errors:
            self.stdout.write(f"  {error}")
        raise CommandError("Validation failed.")
