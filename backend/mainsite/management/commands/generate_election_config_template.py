import json

from django.core.management.base import BaseCommand

_TIMELINE_ENTRY_TEMPLATE = {
    "title": {
        "nl": "string, Dutch title, e.g. Voorlopige uitslag",
        "en": "string, English title, e.g. Provisional result",
    },
    "date": "ISO 8601 datetime, e.g. 2025-12-15T11:00:00",
    "body": {
        "nl": "string, Dutch body text, markdown allowed, e.g. Meer informatie volgt.",
        "en": "string, English body text, markdown allowed, e.g. More information to follow.",
    },
}

ELECTION_CONFIG_TEMPLATE = {
    "election": {
        "id": "string, unique election identifier, e.g. TK2025",
        "label": "string, human-readable election name, e.g. Tweede Kamer Verkiezingen 2025",
        "category": "string, one of TK, EK, PS, WS, GR, EP",
        "date": "ISO 8601 datetime, e.g. 2025-04-12T10:00:00",
        "issue_report_opens_at": "ISO 8601 datetime, e.g. 2025-08-18T11:00:00",
        "issue_report_deadline": "ISO 8601 datetime, e.g. 2025-09-12T10:00:00",
        "report_error_url": "URL string, optional, defaults to empty string if omitted, e.g. https://example.org/meld-een-fout",
        "counting_info_url": "URL string, optional, defaults to empty string if omitted, e.g. https://example.org/telling",
        "voting_url": "URL string, optional, defaults to empty string if omitted, e.g. https://example.org/stemmen",
        "gh_counting_results_branch": "string, optional, GitHub branch name, e.g. auto-tk2025-tel",
        "gh_exchange_branch": "string, optional, GitHub branch name, e.g. auto-tk2025-uit",
    },
    "timeline_entries_cso": [_TIMELINE_ENTRY_TEMPLATE],
    "timeline_entries_dso": [_TIMELINE_ENTRY_TEMPLATE],
    "timeline_entries_default": [_TIMELINE_ENTRY_TEMPLATE],
}


class Command(BaseCommand):
    help = (
        "Print a descriptive election_config.json template (type/description/example per field), "
        "for a human to fill in. Prints to stdout by default; pass --output to write to a file instead. "
        "Validate the filled-in result with validate_election_config before importing it. Never write "
        "the result under a path the object-storage importer scans (election_configs/*.json)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="File path to write the template to. Omit to print to stdout.",
        )

    def handle(self, *args, **options):
        rendered = json.dumps(ELECTION_CONFIG_TEMPLATE, indent=2, ensure_ascii=False)

        output = options["output"]
        if not output:
            self.stdout.write(rendered)
            return

        with open(output, "w") as f:
            f.write(rendered + "\n")
        self.stdout.write(self.style.SUCCESS(f"Wrote template to {output}"))
