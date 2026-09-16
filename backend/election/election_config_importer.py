import logging
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from election.models import ElectionConfig, TimelineEntry, TimelineVariant

logger = logging.getLogger(__name__)

_TIMELINE_VARIANTS = {
    "timeline_entries_cso": TimelineVariant.CSO,
    "timeline_entries_dso": TimelineVariant.DSO,
    "timeline_entries_default": TimelineVariant.DEFAULT,
}

# Changing either of these invalidates everything already imported for the election.
_BRANCH_FIELDS = ("gh_exchange_branch", "gh_counting_results_branch")


def _aware(value: str):
    return timezone.make_aware(datetime.fromisoformat(value))


@transaction.atomic
def import_election_config(data: dict, *, source_hash: str | None = None) -> ElectionConfig:
    """
    Create or update an ElectionConfig (and its timeline entries) from parsed election_config JSON.

    Used by the object-storage importer, so a hand-uploaded election_configs/<ID>.json is applied
    with the same logic regardless of where it was picked up. `seed.py` seeds dev data separately
    and does not call this.
    """
    election_data = data["election"]
    identifier = election_data["id"]

    election_config = ElectionConfig.with_expired.filter(identifier=identifier).first()
    if election_config is None:
        election_config = ElectionConfig(identifier=identifier)
    elif any(election_data.get(field) != getattr(election_config, field) for field in _BRANCH_FIELDS):
        logger.warning(
            "GitHub branch(es) changed for election config %s; wiping previously imported election data.",
            identifier,
        )
        election_config.elections.all().delete()
        election_config.imported_commits.all().delete()

    election_config.category = election_data["category"]
    election_config.label = election_data["label"]
    election_config.date = _aware(election_data["date"])
    election_config.issue_report_opens_at = _aware(election_data["issue_report_opens_at"])
    election_config.issue_report_deadline = _aware(election_data["issue_report_deadline"])
    election_config.report_error_url = election_data.get("report_error_url", "")
    election_config.counting_info_url = election_data.get("counting_info_url", "")
    election_config.voting_url = election_data.get("voting_url", "")
    election_config.gh_counting_results_branch = election_data.get("gh_counting_results_branch")
    election_config.gh_exchange_branch = election_data.get("gh_exchange_branch")
    election_config.source_hash = source_hash
    election_config.save()

    election_config.timeline_entries.all().delete()
    for seed_key, variant in _TIMELINE_VARIANTS.items():
        for entry_data in data.get(seed_key, []):
            TimelineEntry.objects.create(
                election_config=election_config,
                variant=variant,
                title_nl=entry_data["title"]["nl"],
                title_en=entry_data["title"]["en"],
                date=_aware(entry_data["date"]),
                body_nl=entry_data["body"]["nl"],
                body_en=entry_data["body"]["en"],
            )

    return election_config
