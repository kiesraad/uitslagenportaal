import logging
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from redis.exceptions import LockError

from election.models import ElectionCategory, ElectionConfig, ElectionDocument
from eml_import.exceptions import FileAlreadyImported, PDFImporterException
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

# P22 is the centraal stembureau; that region's category comes from the election.
_REGION_CATEGORY_BY_FILE_TYPE = {
    ElectionDocument.FileType.PDF_N10_1: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_N10_2: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_NA14_1: RegionCategory.STEMBUREAU,
    ElectionDocument.FileType.PDF_NA31_1: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_NA31_2: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_NA14_2: RegionCategory.GEMEENTE,
    ElectionDocument.FileType.PDF_O7: RegionCategory.KIESKRING,
}


class _StoragePdf:
    def __init__(self, storage: Storage, key: str):
        self._storage = storage
        self.key = key
        self.name = Path(key).name

    def open(self, mode="rb"):
        return self._storage.open(self.key, mode)


class PDFFileHandler:
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
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
        for name in sorted(self._pdf_names("")):
            try:
                if self._import_pv(_StoragePdf(self.storage, name)):
                    imported += 1
            except IntegrityError, PDFImporterException:
                # A bad file must not stop the rest of this sweep.
                logger.exception("Failed to import proces-verbaal %s", name)
        return imported

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

    def _parse_metadata(self, content: BytesIO, filename: str) -> tuple[str, str, str, str | None, str | None]:
        try:
            document = pdfium.PdfDocument(content.getvalue())
        except Exception as exc:
            raise PDFImporterException(f"{filename} is not a readable PDF") from exc
        try:
            election_id, model, region_name, csb_name, stembureau = (
                document.get_metadata_value(key).strip()
                for key in ("PvElection", "PvModel", "PvRegionName", "PvCsb", "PvStembureau")
            )
        finally:
            document.close()
        if not (election_id and model and region_name):
            raise PDFImporterException(f"{filename} is missing PvElection, PvModel or PvRegionName")
        file_type = ElectionDocument.FileType.from_form_code(model)
        if file_type is None:
            raise PDFImporterException(f"Unknown certified election document type {model} in {filename}")
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
            raise PDFImporterException("Polling-station form needs PvStembureau")
        if config.category == ElectionCategory.WS.value and file_type in POLLING_STATION_PV_FILE_TYPES and not csb_name:
            raise PDFImporterException("Waterschap polling-station form needs PvCsb")

        regions = Region.objects.filter(election__election_config=config, region_category=category)
        if csb_name:
            csb_category = ElectionCategory(config.category).config.csb
            regions = regions.filter(
                Q(csb__region_name__iexact=csb_name)
                | Q(csb__isnull=True, region_name__iexact=csb_name, region_category=csb_category)
            )
        if category == RegionCategory.STEMBUREAU:
            station = (stembureau or "").removeprefix("SB")
            regions = regions.filter(parent__region_name__iexact=region_name, region_number__iendswith=f"::SB{station}")
        else:
            regions = regions.filter(region_name__iexact=region_name)
        try:
            return regions.get()
        except Region.DoesNotExist:
            raise PDFImporterException(f"No {category} {region_name!r} for election {config.identifier}") from None
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
