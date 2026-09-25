import hashlib
import json
import logging

from django.db import transaction

from election.models import ElectionConfig, ElectionDocument, TimelineEntry, TimelineVariant
from election.utils import delete_stored_documents, folder_prefixes, tz_aware_from_isoformat

logger = logging.getLogger(__name__)

_TIMELINE_VARIANTS = {
    "timeline_entries_cso": TimelineVariant.CSO,
    "timeline_entries_dso": TimelineVariant.DSO,
    "timeline_entries_default": TimelineVariant.DEFAULT,
}

# Changing either of these invalidates everything already imported for the election.
_BRANCH_FIELDS = ("gh_exchange_branch", "gh_counting_results_branch")


def hash_election_config_data(data: dict) -> str:
    """
    Hash the parsed election_config data, not the raw file bytes.

    Formatting-only changes to an uploaded file (whitespace, key order) then leave the
    hash unchanged, so they aren't treated as a real content change.
    """
    datadump = json.dumps(data, sort_keys=True)
    return hashlib.sha256(datadump.encode()).hexdigest()


def import_election_config(data: dict) -> ElectionConfig:
    """
    Create or update an ElectionConfig (and its timeline entries) from parsed election_config JSON.

    Used by the object-storage importer, so a hand-uploaded election_configs/<ID>.json is applied
    with the same logic regardless of where it was picked up. `seed.py` seeds dev data separately
    and does not call this.
    """
    election_data = data["election"]
    identifier = election_data["id"]
    source_hash = hash_election_config_data(data)

    election_config = ElectionConfig.with_expired.filter(identifier=identifier).first()
    if election_config is not None and any(
        election_data.get(field) != getattr(election_config, field) for field in _BRANCH_FIELDS
    ):
        _wipe_election_data(election_config)

    return _save_election_config(election_config, identifier, election_data, data, source_hash)


def _wipe_election_data(election_config: ElectionConfig) -> None:
    logger.warning(
        "GitHub branch(es) changed for election config %s; wiping previously imported election data.",
        election_config.identifier,
    )

    # Blanked and committed in its own transaction, ahead of the wipe below.
    for field in _BRANCH_FIELDS:
        setattr(election_config, field, None)
    election_config.save(update_fields=_BRANCH_FIELDS)

    with transaction.atomic():
        # The rows are the only reference to the stored documents, so the keys have
        # to be collected before the cascade deletes ElectionDocument along with them.
        storage_keys = list(
            ElectionDocument.all_objects.filter(region__election__election_config=election_config).values_list(
                "storage_key", flat=True
            )
        )
        prefixes = folder_prefixes(storage_keys)

        election_config.elections.all().delete()
        election_config.imported_commits.all().delete()

    _, failed = delete_stored_documents(storage_keys, prefixes)
    if failed:
        logger.warning(
            "%d stored document(s) for election config %s could not be deleted and are now orphaned: %s",
            len(failed),
            election_config.identifier,
            failed,
        )


@transaction.atomic
def _save_election_config(
    election_config: ElectionConfig | None, identifier: str, election_data: dict, data: dict, source_hash: str
) -> ElectionConfig:
    if election_config is None:
        election_config = ElectionConfig(identifier=identifier)

    election_config.category = election_data["category"]
    election_config.label = election_data["label"]
    election_config.date = tz_aware_from_isoformat(election_data["date"])
    election_config.issue_report_opens_at = tz_aware_from_isoformat(election_data["issue_report_opens_at"])
    election_config.issue_report_deadline = tz_aware_from_isoformat(election_data["issue_report_deadline"])
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
                date=tz_aware_from_isoformat(entry_data["date"]),
                body_nl=entry_data["body"]["nl"],
                body_en=entry_data["body"]["en"],
            )

    return election_config
