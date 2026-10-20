from botocore.exceptions import ConnectionError as S3ConnectionError
from django.db import DatabaseError
from django.db.models import Count, Q

from election.models import ElectionDocument
from mainsite.celery import app
from mainsite.models import RegionCategory
from region.models import Region
from region.polling_station_pv_archive import POLLING_STATION_PV_FILE_TYPES, write_polling_station_pv_zip


@app.task(
    ignore_result=True,
    autoretry_for=[DatabaseError, S3ConnectionError],
    retry_backoff=5,
    max_retries=2,
)
def build_polling_station_pv_zip(gemeente_id: int) -> str | None:
    """Write one gemeente's polling-station PV zip to object storage."""
    try:
        gemeente = (
            Region.objects.select_related("election__election_config")
            .annotate(
                sb_cnt=Count(
                    "children",
                    filter=Q(children__region_category=RegionCategory.STEMBUREAU),
                    distinct=True,
                ),
                # Corrections on the same polling station do not raise the count.
                sb_with_pv_cnt=Count(
                    "children",
                    filter=Q(children__documents__file_type__in=POLLING_STATION_PV_FILE_TYPES),
                    distinct=True,
                ),
            )
            .get(pk=gemeente_id, region_category=RegionCategory.GEMEENTE)
        )
    except Region.DoesNotExist:
        return None
    key, size = write_polling_station_pv_zip(gemeente)

    # Sync the ElectionDocument in the Db with the stored zip-files (or remove it if the zip is removed)
    if key:
        ElectionDocument.objects.update_or_create(
            dict(
                storage_key=key,
                region=gemeente,
                content_type="application/zip",
                file_type=ElectionDocument.FileType.PDF_SB_ZIP,
                size=size,
                metadata={"total": gemeente.sb_cnt, "present": gemeente.sb_with_pv_cnt},
            ),
            file_type=ElectionDocument.FileType.PDF_SB_ZIP,
            region=gemeente,
        )
    else:
        ElectionDocument.objects.filter(file_type=ElectionDocument.FileType.PDF_SB_ZIP, region=gemeente).delete()

    return key
