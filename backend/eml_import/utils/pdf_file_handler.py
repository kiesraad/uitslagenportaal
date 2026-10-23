import logging
from datetime import timedelta
from functools import cached_property
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from redis.exceptions import LockError

from election.models import ElectionCategory, ElectionConfig, ElectionDocument
from eml_import.exceptions import FileAlreadyImported, InvalidPDFException, PDFImporterException
from eml_import.models import ImportedFileHash
from mainsite.models import RegionCategory
from region.models import Region
from region.polling_station_pv_archive import POLLING_STATION_PV_FILE_TYPES

logger = logging.getLogger(__name__)

# Seconds before the sweep lock expires on its own, so a worker that dies mid-import
# does not block the next Beat tick forever. Kept at the Celery hard limit so a
# long sweep is not overlapped before the worker is killed.
LOCK_TIMEOUT = 30 * 60

# The results box shows one page. Twice the PDF point size stays sharp at that width.
_PREVIEW_SCALE = 2

DEFAULT_PV_DIRECTORY = "pv_import_queue"

# A PV is moved here once it is invalid or has used up its retries, so it is no longer tried.
FAILED_PV_DIRECTORY = "pv_import_failed"
# Waits after each failed try; a region whose EML is not imported yet may take a day to arrive.
RETRY_DELAYS = (
    timedelta(minutes=5),
    timedelta(minutes=20),
    timedelta(hours=1),
    timedelta(hours=12),
    timedelta(hours=24),
)
# Outlasts the whole schedule, so the retry state is not evicted halfway.
RETRY_STATE_TIMEOUT = 2 * 24 * 60 * 60

# P22 is the centraal stembureau; that region's category comes from the election.
_REGION_CATEGORY_BY_FILE_TYPE = {
    ElectionDocument.FileType.PDF_N10_1: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_N10_2: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_NA14_1: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_NA31_1: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_NA31_2: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_NA31_2_B1: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_NA31_2_B2: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_NA14_2: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_NA14_2_B1: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_O7: RegionCategory.KIESKRING,
    ElectionDocument.FileType.PDF_P1F_1: RegionCategory.KIESKRING,
}


class _StoragePdf:
    def __init__(self, storage: Storage, key: str):
        self._storage = storage
        self.key = key
        self.name = Path(key).name

    def open(self, mode="rb"):
        return self._storage.open(self.key, mode)

    @cached_property
    def retry_key(self) -> str:
        # A file uploaded again under the same name starts a new retry schedule.
        modified = self._storage.get_modified_time(self.key).timestamp()
        return f"pdf-importer-retry:{self.key}:{modified}"


class PDFFileHandler:
    def __init__(self, storage: Storage, directory: str | None = None):
        super().__init__()
        self.storage = storage
        self.root_directory = directory or DEFAULT_PV_DIRECTORY
        self.archive_municipality_ids: set[int] = set()

    @staticmethod
    def cache_lock_key() -> str:
        """The cache key of the lock held while proces-verbalen are imported."""
        return "pdf-importer"

    def run(self) -> int:
        self.archive_municipality_ids = set()
        # One sweep at a time, so two workers cannot import the same PDF twice
        lock = cache.lock(self.cache_lock_key(), timeout=LOCK_TIMEOUT, blocking=False)
        if not lock.acquire():
            logger.warning("Could not acquire lock, PDFFileHandler is already running")
            return 0

        try:
            return self._run_import()
        finally:
            try:
                lock.release()
            except LockError:
                logger.warning("Lock expired while importing proces-verbalen")

    def _run_import(self) -> int:
        imported = 0
        for name in sorted(self._pdf_names(self.root_directory)):
            file = _StoragePdf(self.storage, name)
            retry = cache.get(file.retry_key)
            if retry and timezone.now() < retry["retry_at"]:
                continue
            try:
                if self._import_pv(file):
                    imported += 1
            except InvalidPDFException as exc:
                # A bad file must not stop the rest of this sweep. An invalid PDF stays invalid, so it is not retried.
                logger.error("Failed to import proces-verbaal %s: %s", name, exc)
                self._move_to_failed(file)
            except (IntegrityError, PDFImporterException) as exc:
                logger.error("Failed to import proces-verbaal %s: %s", name, exc)
                self._schedule_retry(file, retry["failures"] if retry else 0)
            else:
                cache.delete(file.retry_key)
        return imported

    def _schedule_retry(self, file: _StoragePdf, earlier_failures: int) -> None:
        """Retry a failure that may resolve itself, such as a region whose EML is not imported yet."""
        if earlier_failures >= len(RETRY_DELAYS):
            self._move_to_failed(file)
            return
        retry = {"failures": earlier_failures + 1, "retry_at": timezone.now() + RETRY_DELAYS[earlier_failures]}
        cache.set(file.retry_key, retry, timeout=RETRY_STATE_TIMEOUT)

    def _move_to_failed(self, file: _StoragePdf) -> None:
        with file.open("rb") as handle:
            moved_key = self.storage.save(f"{FAILED_PV_DIRECTORY}/{file.name}", handle)
        self.storage.delete(file.key)
        cache.delete(file.retry_key)
        logger.error("Gave up on proces-verbaal %s, moved to %s", file.key, moved_key)

    def _pdf_names(self, directory: str):
        directories, filenames = self.storage.listdir(directory)
        for filename in filenames:
            if filename.endswith(".pdf"):
                yield f"{directory}/{filename}" if directory else filename
        for name in directories:
            yield from self._pdf_names(f"{directory}/{name}" if directory else name)

    def _import_pv(self, file: _StoragePdf) -> bool:
        with file.open("rb") as handle:
            content = BytesIO(handle.read())
        election_id, file_type, region_name, csb_name, stembureau = self._parse_metadata(content, file.name)
        config = self._election_config(election_id)
        region = self._region(config, file_type, region_name, csb_name, stembureau)

        try:
            with ImportedFileHash.if_not_imported(content, region.election):
                self._store(content, file.name, config.identifier, region, file_type)
        except FileAlreadyImported:
            logger.info("Skipping duplicate proces-verbaal %s", file.name)
            self._delete_from_import_storage(file)
            return False

        self._delete_from_import_storage(file)

        if file_type in POLLING_STATION_PV_FILE_TYPES and region.parent_id:
            self.archive_municipality_ids.add(region.parent_id)

        logger.info("Imported %s onto %s %s", file.name, region.region_category, region.region_name)
        return True

    def _delete_from_import_storage(self, file: _StoragePdf) -> None:
        """Remove a processed file from the inbox. A failed import must not call this."""
        try:
            self.storage.delete(file.key)
        except Exception:
            logger.exception("Failed to delete processed proces-verbaal %s from import storage", file.key)

    def _parse_metadata(
        self, content: BytesIO, filename: str
    ) -> tuple[str, ElectionDocument.FileType, str, str | None, str | None]:
        try:
            document = pdfium.PdfDocument(content.getvalue())
        except Exception as exc:
            raise InvalidPDFException(f"{filename} is not a readable PDF") from exc
        try:
            election_id, model, region_name, csb_name, stembureau = (
                document.get_metadata_value(key).strip()
                for key in ("PvElection", "PvModel", "PvRegionName", "PvCsb", "PvStembureau")
            )
        finally:
            document.close()
        if not (election_id and model and region_name):
            raise InvalidPDFException(f"{filename} is missing PvElection, PvModel or PvRegionName")
        file_type = ElectionDocument.FileType.from_form_code(model)
        if file_type is None:
            raise InvalidPDFException(f"Unknown certified election document type {model} in {filename}")
        return election_id, file_type, region_name, csb_name or None, stembureau or None

    def _election_config(self, election_id: str) -> ElectionConfig:
        try:
            return ElectionConfig.with_expired.get(identifier=election_id)
        except ElectionConfig.DoesNotExist:
            raise PDFImporterException(f"Election {election_id} is not configured") from None

    def _region_category(self, config: ElectionConfig, file_type: str) -> str:
        if file_type in (ElectionDocument.FileType.PDF_P22_1, ElectionDocument.FileType.PDF_P22_2):
            return ElectionCategory(config.category).config.csb
        return _REGION_CATEGORY_BY_FILE_TYPE[file_type]

    def _region(
        self,
        config: ElectionConfig,
        file_type: str,
        region_name: str,
        csb_name: str | None,
        stembureau: str | None,
    ) -> Region:
        category = self._region_category(config, file_type)
        if category == RegionCategory.STEMBUREAU and not stembureau:
            raise InvalidPDFException("Polling-station form needs PvStembureau")
        if config.category == ElectionCategory.WS.value and file_type in POLLING_STATION_PV_FILE_TYPES and not csb_name:
            raise InvalidPDFException("Waterschap polling-station form needs PvCsb")

        regions = Region.objects.filter(election__election_config=config, region_category=category)
        if csb_name:
            csb_category = ElectionCategory(config.category).config.csb
            regions = regions.filter(
                Q(csb__region_name__iexact=csb_name)
                | Q(csb__isnull=True, region_name__iexact=csb_name, region_category=csb_category)
            )
        if category == RegionCategory.STEMBUREAU:
            station = (stembureau or "").removeprefix("SB").lstrip("0")
            if not station.isdigit():
                raise InvalidPDFException(f"PvStembureau {stembureau!r} is not a stembureau number")
            # Some EML pads the stembureau number: 0770::SB08.
            regions = regions.filter(
                parent__region_name__iexact=region_name, region_number__iregex=rf"::SB0*{station}$"
            )
            missing = f"No stembureau {station} in {region_name!r}"
        else:
            regions = regions.filter(region_name__iexact=region_name)
            missing = f"No {category} {region_name!r}"
        try:
            return regions.get()
        except Region.DoesNotExist:
            raise PDFImporterException(f"{missing} for election {config.identifier}") from None
        except Region.MultipleObjectsReturned:
            raise PDFImporterException(
                f"Several {category} regions match {region_name!r} for election {config.identifier}"
            ) from None

    def _preview_png(self, content: BytesIO) -> bytes:
        document = pdfium.PdfDocument(content.getvalue())
        try:
            page = document[0]
            bitmap = page.render(scale=_PREVIEW_SCALE)
            try:
                image = bitmap.to_pil()
            finally:
                bitmap.close()
                page.close()
        finally:
            document.close()

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @transaction.atomic
    def _store(self, content: BytesIO, filename: str, election_id: str, region: Region, file_type: str) -> None:
        preview = self._preview_png(content)
        storage_key = f"{election_id}/{filename}"
        size = content.getbuffer().nbytes

        if file_type not in ElectionDocument.CORRECTION_FILE_TYPES:
            ElectionDocument.objects.filter(region=region, file_type=file_type).archive()

        content.seek(0)
        stored_key = default_storage.save(storage_key, File(content))
        default_storage.save(Path(stored_key).with_suffix(".png").as_posix(), ContentFile(preview))

        ElectionDocument.objects.create(
            region=region,
            file_type=file_type,
            storage_key=stored_key,
            content_type="application/pdf",
            size=size,
        )
