import json
import logging

from django.core.files.storage import default_storage

from election.election_config_importer import hash_election_config_data, import_election_config
from election.models import ElectionConfig
from election.utils import tz_aware_from_isoformat, visibility_cutoff

logger = logging.getLogger(__name__)

# Folder in the object storage bucket where election_config JSON files are placed by hand
# ahead of an election, e.g. election_configs/AB2023.json.
ELECTION_CONFIGS_PREFIX = "election_configs/"


def import_new_election_configs() -> int:
    """
    Scan the bucket for election_config JSON files and import any that are new or changed.

    A file is skipped once the hash of its parsed data matches ElectionConfig.source_hash for
    that identifier, so re-polling an unchanged upload is a no-op. Hashing the parsed data
    rather than the raw bytes means formatting-only re-uploads (whitespace, key order) are
    also skipped. Returns the number imported.

    Uses the generic Storage API (listdir/open) rather than boto3 directly, so it works
    against any configured backend, including the in-memory one used in tests.
    """
    imported = 0
    known_hashes = dict(ElectionConfig.with_expired.exclude(source_hash=None).values_list("identifier", "source_hash"))

    try:
        _, filenames = default_storage.listdir(ELECTION_CONFIGS_PREFIX)
    except FileNotFoundError:
        # No election_configs/ folder yet, e.g. a fresh bucket or an in-memory test backend.
        filenames = []

    for filename in filenames:
        if not filename.endswith(".json"):
            continue

        key = f"{ELECTION_CONFIGS_PREFIX}{filename}"

        with default_storage.open(key, "rb") as fh:
            content = fh.read()

        try:
            data = json.loads(content)
            identifier = data["election"]["id"]
            election_date = tz_aware_from_isoformat(data["election"]["date"])
        except Exception:
            logger.exception("Failed to parse election config from %s", key)
            continue

        if filename.removesuffix(".json") != identifier:
            logger.warning(
                "election_config at %s declares id %s, which does not match the file name; importing anyway.",
                key,
                identifier,
            )

        # Skip import if the election date is before the visibility cutoff
        if election_date < visibility_cutoff():
            logger.info("Skipping import of election config %s: election is expired", identifier)
            continue

        # Keyed on the id the file itself declares, not the file name, so a mismatch
        # (logged above) still dedupes correctly on every later poll.
        if known_hashes.get(identifier) == hash_election_config_data(data):
            continue

        logger.info("Importing election config %s from %s", identifier, key)
        try:
            import_election_config(data)
        except Exception:
            logger.exception("Failed to import election config from %s", key)
            continue

        imported += 1

    return imported

def remove_expired_election_configs(identifiers: list[str]) -> list[str]:
    try:
        _, filenames = default_storage.listdir(ELECTION_CONFIGS_PREFIX)
    except FileNotFoundError:
        # No election_configs/ folder yet, e.g. a fresh bucket or an in-memory test backend.
        filenames = []

    deleted = []
    for filename in filenames:
        if not filename.endswith(".json"):
            continue

        path = f"{ELECTION_CONFIGS_PREFIX}{filename}"
        try:
            with default_storage.open(path, "rb") as fh:
                data = json.load(fh)
        except Exception:
            logger.exception("Failed to parse election config from %s", path)
            continue

        # Skip files not in the list
        if data["election"]["id"] not in identifiers:
            continue

        election_date = tz_aware_from_isoformat(data["election"]["date"])
        if election_date < visibility_cutoff():
            default_storage.delete(path)
            deleted += [path]
            logger.info("Deleted expired election config from %s", path)
        else:
            logger.info("Skipped deleting election config from %s, not expired", path)

        return deleted




