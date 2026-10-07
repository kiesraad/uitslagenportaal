import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlencode

from django.core.files import File
from django.core.files.storage import default_storage
from django.db.models import Sum
from django.urls import reverse

from election.models import ElectionDocument
from mainsite.models import RegionCategory

# The original polling-station form and every correction on it belong in the zip.
POLLING_STATION_PV_FILE_TYPES = (
    ElectionDocument.FileType.PDF_N10_1,
    ElectionDocument.FileType.PDF_N10_2,
    ElectionDocument.FileType.PDF_NA14_1,
)
_FORM_ORDER = {file_type: index for index, file_type in enumerate(POLLING_STATION_PV_FILE_TYPES)}


def polling_station_pv_documents(municipality):
    return ElectionDocument.objects.filter(
        region__parent=municipality,
        region__region_category=RegionCategory.STEMBUREAU,
        file_type__in=POLLING_STATION_PV_FILE_TYPES,
    ).select_related("region__parent", "region__election__election_config")


def polling_station_pv_zip_storage_key(municipality):
    return f"{municipality.election.election_config.identifier}/polling-station-pvs/{municipality.pk}.zip"


def polling_station_pv_summary(municipality, request=None):
    """Counts and download URL for the municipality page. None until the zip is in storage."""
    if municipality.region_category != RegionCategory.municipality:
        return None

    documents = polling_station_pv_documents(municipality)
    # Corrections on the same polling station do not raise the count.
    present_count = documents.values("region_id").distinct().count()
    if present_count == 0:
        return None
    if not default_storage.exists(polling_station_pv_zip_storage_key(municipality)):
        return None

    query = {}
    if request is not None:
        query = {key: request.GET[key] for key in ("csb", "parent_region") if request.GET.get(key)}
    url = reverse(
        "polling-station-pv-archive",
        kwargs={"election_config": municipality.election.election_config.slug, "region": municipality.slug},
    )
    if query:
        url = f"{url}?{urlencode(query)}"

    return {
        "url": url,
        "present_count": present_count,
        "total_count": municipality.children.filter(region_category=RegionCategory.STEMBUREAU).count(),
        "size": documents.aggregate(total=Sum("size"))["total"] or 0,
    }


def _ordered_polling_station_pvs(documents):
    return sorted(
        documents,
        key=lambda document: (
            document.region.region_number or "",
            _FORM_ORDER[document.file_type],
            document.created_at,
        ),
    )


def write_polling_station_pv_zip(municipality):
    """Write the municipality zip to object storage, or delete it when no forms remain."""
    documents = list(polling_station_pv_documents(municipality))
    key = polling_station_pv_zip_storage_key(municipality)
    if not documents:
        if default_storage.exists(key):
            default_storage.delete(key)
        return None

    with tempfile.TemporaryFile() as tmp:
        # PDFs are stored uncompressed; they are already compressed.
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as archive:
            for document in _ordered_polling_station_pvs(documents):
                with default_storage.open(document.storage_key, "rb") as handle:
                    archive.writestr(document.download_filename, handle.read())
        tmp.seek(0)
        if default_storage.exists(key):
            default_storage.delete(key)
        default_storage.save(key, File(tmp, name=Path(key).name))
    return key
