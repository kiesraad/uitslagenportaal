import logging
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q

from election.models import ElectionCategory, ElectionConfig, ElectionDocument
from eml_import.exceptions import PDFImporterException
from mainsite.models import RegionCategory
from region.models import Region

logger = logging.getLogger(__name__)

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
        self._key = key
        self.name = Path(key).name
        self.stem = Path(key).stem

    def open(self, mode="rb"):
        return self._storage.open(self._key, mode)


class PDFFileHandler:
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage

    def run(self) -> int:
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
        election_id, csb_name, file_type, region_token = self._parse_filename(file)
        # A later upload of the same name is left unnoticed.
        if ElectionDocument.objects.filter(storage_key=f"{election_id}/{file.name}").exists():
            return False

        config = self._election_config(election_id)
        region = self._region(config, file_type, csb_name, region_token)
        with file.open("rb") as handle:
            content = BytesIO(handle.read())
        self._store(content, file.name, config.identifier, region, file_type)

        logger.info("Imported %s onto %s %s", file.name, region.region_category, region.region_name)
        return True

    def _parse_filename(self, file: _StoragePdf) -> tuple[str, str, str, str]:
        parts = file.stem.split("_", 3)
        if len(parts) != 4 or not all(parts):
            raise PDFImporterException(f"{file.name} does not match {{election}}_{{csb}}_{{file_type}}_{{region}}.pdf")
        election_id, csb_name, form_code, region_token = parts
        file_type = ElectionDocument.FileType.from_form_code(form_code)
        if file_type is None:
            raise PDFImporterException(f"Unknown certified election document type {form_code} in {file.name}")
        return election_id, csb_name, file_type, region_token

    def _election_config(self, election_id: str) -> ElectionConfig:
        try:
            return ElectionConfig.with_expired.get(identifier=election_id)
        except ElectionConfig.DoesNotExist:
            raise PDFImporterException(f"Election {election_id} is not configured") from None

    def _region_category(self, config: ElectionConfig, file_type: str) -> str:
        if file_type in (ElectionDocument.FileType.PDF_P22_1, ElectionDocument.FileType.PDF_P22_2):
            return ElectionCategory(config.category).config.csb
        return _REGION_CATEGORY_BY_FILE_TYPE[file_type]

    def _region(self, config: ElectionConfig, file_type: str, csb_name: str, region_token: str) -> Region:
        category = self._region_category(config, file_type)
        # A stembureau number repeats in every gemeente; the stored id carries the gemeente (0203::SB1).
        lookup = (
            {"region_number": region_token} if category == RegionCategory.STEMBUREAU else {"region_name": region_token}
        )
        csb_category = ElectionCategory(config.category).config.csb
        belongs_to_csb = Q(csb__region_name=csb_name) | Q(
            csb__isnull=True,
            region_name=csb_name,
            region_category=csb_category,
        )
        try:
            return Region.objects.get(
                belongs_to_csb,
                election__election_config=config,
                region_category=category,
                **lookup,
            )
        except Region.DoesNotExist:
            raise PDFImporterException(
                f"No {category} {region_token!r} under CSB {csb_name!r} for election {config.identifier}"
            ) from None
        except Region.MultipleObjectsReturned:
            raise PDFImporterException(
                f"Several {category} regions match {region_token!r} under CSB {csb_name!r} "
                f"for election {config.identifier}"
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
