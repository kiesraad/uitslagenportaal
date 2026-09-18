from calendar import monthrange
from datetime import timedelta

from django.core.files.storage import default_storage
from django.utils import timezone

VISIBILITY_MONTHS = 3  # currently hardcoded at 3 months
DELETION_GRACE_DAYS = 7


def visibility_cutoff():
    now = timezone.now()
    month = now.month - VISIBILITY_MONTHS
    year = now.year
    if month <= 0:
        month += 12
        year -= 1
    last_day_of_month = monthrange(year, month)[1]
    return now.replace(year=year, month=month, day=min(now.day, last_day_of_month))


def deletion_cutoff():
    return visibility_cutoff() - timedelta(days=DELETION_GRACE_DAYS)


def folder_prefixes(storage_keys):
    """Reduce storage keys to the set of top-level folders holding them.

    The keys are relative paths of the form "<identifier>/<body>/<file>",
    so the first segment is the per-election folder.
    """
    prefixes = set()
    for key in storage_keys:
        head, separator, _ = key.partition("/")
        if separator and head:
            prefixes.add(head)
    return prefixes


def delete_stored_documents(storage_keys, prefixes):
    """Remove documents from object storage, deleting whole folders by prefix where possible."""
    bucket = getattr(default_storage, "bucket", None)
    if bucket is None:
        return _delete_keys(storage_keys)

    deleted = 0
    failed = []
    for prefix in sorted(prefixes):
        try:
            responses = bucket.objects.filter(Prefix=f"{prefix}/").delete()
        except Exception as exc:
            failed.append((f"{prefix}/", exc))
            continue

        for response in responses:
            deleted += len(response.get("Deleted", []))
            for error in response.get("Errors", []):
                failed.append((error.get("Key", f"{prefix}/"), error.get("Message", "delete failed")))

    # Anything that was not under a folder is still present.
    loose_keys = [key for key in storage_keys if key.partition("/")[0] not in prefixes]
    loose_deleted, loose_failed = _delete_keys(loose_keys)
    return deleted + loose_deleted, failed + loose_failed


def _delete_keys(storage_keys):
    deleted = 0
    failed = []
    for key in storage_keys:
        try:
            default_storage.delete(key)
        except Exception as exc:
            failed.append((key, exc))
        else:
            deleted += 1
    return deleted, failed
