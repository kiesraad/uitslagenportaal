import logging
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from election.models import CertifiedElectionDocument, ElectionCategory, ElectionConfig
from eml_import.exceptions import EMLImporterException
from mainsite.models import RegionCategory
from region.models import Region

logger = logging.getLogger(__name__)

# The results box shows one page. Twice the PDF point size stays sharp at that width.
_PREVIEW_SCALE = 2

# P22 is the centraal stembureau; that region's category comes from the election.
_REGION_CATEGORY_BY_FILE_TYPE = {
    CertifiedElectionDocument.FileType.N10_1: RegionCategory.STEMBUREAU,
    CertifiedElectionDocument.FileType.N10_2: RegionCategory.STEMBUREAU,
    CertifiedElectionDocument.FileType.NA14_1: RegionCategory.STEMBUREAU,
    CertifiedElectionDocument.FileType.NA31_1: RegionCategory.GEMEENTE,
    CertifiedElectionDocument.FileType.NA31_2: RegionCategory.GEMEENTE,
    CertifiedElectionDocument.FileType.NA14_2: RegionCategory.GEMEENTE,
    CertifiedElectionDocument.FileType.O7: RegionCategory.KIESKRING,
}


class FolderPDFFileHanlder:
    def __init__(self, folder: Path):
        super().__init__()
        self.folder = folder

    def run(self):
        files = sorted(self.folder.rglob("*.pdf"))
        for file in files:
            self._import_pv(file)

    def _import_pv(self, file: Path) -> None:
        election_id, file_type, region_token = self._parse_filename(file)
        config = self._election_config(election_id)
        region = self._region(config, file_type, region_token)
        self._store(file, config.identifier, region, file_type)
        logger.info("Imported %s onto %s %s", file.name, region.region_category, region.region_name)

    def _parse_filename(self, file: Path) -> tuple[str, str, str]:
        parts = file.stem.split("_", 2)
        if len(parts) != 3 or not all(parts):
            raise EMLImporterException(f"{file.name} does not match {{election}}_{{file_type}}_{{region}}.pdf")
        election_id, file_type, region_token = parts
        if file_type not in CertifiedElectionDocument.FileType.values:
            raise EMLImporterException(f"Unknown certified election document type {file_type} in {file.name}")
        return election_id, file_type, region_token

    def _election_config(self, election_id: str) -> ElectionConfig:
        try:
            return ElectionConfig.with_expired.get(identifier=election_id)
        except ElectionConfig.DoesNotExist:
            raise EMLImporterException(f"Election {election_id} is not configured") from None

    def _region_category(self, config: ElectionConfig, file_type: str) -> str:
        if file_type in (CertifiedElectionDocument.FileType.P22_1, CertifiedElectionDocument.FileType.P22_2):
            return ElectionCategory(config.category).config.csb
        return _REGION_CATEGORY_BY_FILE_TYPE[file_type]

    def _region(self, config: ElectionConfig, file_type: str, region_token: str) -> Region:
        category = self._region_category(config, file_type)
        # A stembureau number repeats in every gemeente; the stored id carries the gemeente (0203::SB1).
        lookup = (
            {"region_number": region_token} if category == RegionCategory.STEMBUREAU else {"region_name": region_token}
        )
        try:
            return Region.objects.get(
                election__election_config=config,
                region_category=category,
                **lookup,
            )
        except Region.DoesNotExist:
            raise EMLImporterException(f"No {category} {region_token!r} for election {config.identifier}") from None
        except Region.MultipleObjectsReturned:
            raise EMLImporterException(
                f"Several {category} regions match {region_token!r} for election {config.identifier}"
            ) from None

    def _preview_png(self, file: Path) -> bytes:
        document = pdfium.PdfDocument(file)
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
    def _store(self, file: Path, election_id: str, region: Region, file_type: str) -> None:
        preview = self._preview_png(file)
        storage_key = f"{election_id}/{file.name}"

        with file.open("rb") as handle:
            stored_key = default_storage.save(storage_key, File(handle))
        default_storage.save(Path(stored_key).with_suffix(".png").as_posix(), ContentFile(preview))

        CertifiedElectionDocument.objects.create(
            region=region,
            file_type=file_type,
            storage_key=stored_key,
            content_type="application/pdf",
            size=file.stat().st_size,
        )
