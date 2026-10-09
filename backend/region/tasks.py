from botocore.exceptions import ConnectionError as S3ConnectionError
from django.db import DatabaseError

from mainsite.celery import app
from mainsite.models import RegionCategory
from region.models import Region
from region.polling_station_pv_archive import write_polling_station_pv_zip


@app.task(
    ignore_result=True,
    autoretry_for=[DatabaseError, S3ConnectionError],
    retry_backoff=5,
    max_retries=2,
)
def build_polling_station_pv_zip(gemeente_id: int) -> str | None:
    """Write one gemeente's polling-station PV zip to object storage."""
    try:
        gemeente = Region.objects.select_related("election__election_config").get(
            pk=gemeente_id,
            region_category=RegionCategory.GEMEENTE,
        )
    except Region.DoesNotExist:
        return None
    return write_polling_station_pv_zip(gemeente)
