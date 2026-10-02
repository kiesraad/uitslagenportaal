import io
import zipfile
from urllib.parse import urlencode

from django.core.files.storage import default_storage
from django.db.models import Sum
from django.urls import reverse

from election.models import ElectionDocument
from mainsite.models import RegionCategory

# The original polling-station form and its corrigendum both belong in the zip.
_POLLING_STATION_PV_FILE_TYPES = (
    ElectionDocument.FileType.PDF_N10_1,
    ElectionDocument.FileType.PDF_N10_2,
    ElectionDocument.FileType.PDF_NA14_1,
)
_FORM_ORDER = {file_type: index for index, file_type in enumerate(_POLLING_STATION_PV_FILE_TYPES)}


def polling_station_pv_documents(gemeente):
    return ElectionDocument.objects.filter(
        region__parent=gemeente,
        region__region_category=RegionCategory.STEMBUREAU,
        file_type__in=_POLLING_STATION_PV_FILE_TYPES,
    ).select_related("region")


def polling_station_pv_summary(gemeente, request=None):
    """Counts and download URL for the gemeente page. None until the first form is in."""
    if gemeente.region_category != RegionCategory.GEMEENTE:
        return None

    documents = polling_station_pv_documents(gemeente)
    # A corrigendum on the same polling station does not raise the count.
    present_count = documents.values("region_id").distinct().count()
    if present_count == 0:
        return None

    query = {}
    if request is not None:
        query = {key: request.GET[key] for key in ("csb", "parent_region") if request.GET.get(key)}
    url = reverse(
        "polling-station-pv-archive",
        kwargs={"election_config": gemeente.election.election_config.slug, "region": gemeente.slug},
    )
    if query:
        url = f"{url}?{urlencode(query)}"

    return {
        "url": url,
        "present_count": present_count,
        "total_count": gemeente.children.filter(region_category=RegionCategory.STEMBUREAU).count(),
        "size": documents.aggregate(total=Sum("size"))["total"] or 0,
    }


def _entry_name(document) -> str:
    number = (document.region.region_number or "").replace("::", "-").replace("/", "-")
    name = document.region.region_name.replace("/", "-").replace("\\", "-")
    form = str(document.file_type).removeprefix("PDF_")
    return f"{number} {name} {form}.pdf".strip()


class _ChunkWriter(io.RawIOBase):
    """Collects the bytes a ZipFile writes, so each member can be streamed out."""

    def __init__(self):
        self._chunks: list[bytes] = []

    def writable(self):
        return True

    def write(self, data):
        self._chunks.append(bytes(data))
        return len(data)

    def pop(self) -> bytes:
        chunks, self._chunks = self._chunks, []
        return b"".join(chunks)


def iter_polling_station_pv_zip(documents):
    """PDFs are stored uncompressed; they are already compressed."""
    ordered = sorted(
        documents,
        key=lambda document: (document.region.region_number or "", _FORM_ORDER[document.file_type]),
    )
    writer = _ChunkWriter()
    with zipfile.ZipFile(writer, "w", compression=zipfile.ZIP_STORED) as archive:
        for document in ordered:
            with default_storage.open(document.storage_key, "rb") as handle:
                archive.writestr(_entry_name(document), handle.read())
            chunk = writer.pop()
            if chunk:
                yield chunk
    tail = writer.pop()
    if tail:
        yield tail
