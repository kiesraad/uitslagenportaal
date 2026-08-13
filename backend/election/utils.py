from calendar import monthrange
from datetime import timedelta

from django.utils import timezone

# TODO: discuss if this is the 'best' approach
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
