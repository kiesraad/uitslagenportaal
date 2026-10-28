import logging
import re
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

from django.core.files.storage import default_storage
from django.utils import timezone

from election.models import Election, ElectionConfig, ElectionDocument
from eml_import.exceptions import EMLImporterException, FileAlreadyImported
from eml_import.models import ImportedFileHash
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.eml_type import EmlType
from region.models import Region


class BaseImporter(ABC):
    file_type: ElectionDocument.FileType

    def __init__(self, file_path: Path | NamedBytesIO, *args, **kwargs):
        self.file_path = file_path
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.election: Election | None = None

    def parse(self):
        if self.election is None:
            raise EMLImporterException("Election not loaded before calling parse()")

        try:
            with ImportedFileHash.if_not_imported(self.file_path, self.election):
                self._parse_data()
        except ElectionConfig.DoesNotExist:
            self.logger.warning("Election is not configured, skipping %s data import", self.file_type.value)
        except FileAlreadyImported:
            self.logger.info(
                "\033[32mSkipping duplicate %s file %s\033[0m",
                self.file_type.value,
                self.file_path,
            )

    @abstractmethod
    def _parse_data(self): ...


class EMLStorageMixin:
    """Stores the imported EML file as a document of a region."""

    eml_type: EmlType
    file_type: ElectionDocument.FileType
    file_path: Path | NamedBytesIO
    election: Election | None

    def _store_eml(self, region: Region) -> None:
        election_config = self.election.election_config
        parent_number, parent_name = (
            (region.parent.region_number, region.parent.region_name) if region.parent else (None, None)
        )
        filename = "_".join(
            filter(
                None,
                [
                    election_config.identifier,
                    self.eml_type.label,
                    parent_number,
                    parent_name,
                    region.region_number,
                    region.region_name,
                    timezone.now().strftime("%Y%m%dT%H%M%S%f"),
                ],
            )
        )
        filename = re.sub(r"[^A-Za-z0-9_-]", "", filename.replace(" ", "_"))
        file_path = f"{election_config.identifier}/{filename}.eml.xml"

        if isinstance(self.file_path, Path):
            file_content = BytesIO(self.file_path.read_bytes())
        else:
            file_content = self.file_path
        file_content.seek(0)
        size = len(file_content.getvalue())
        stored_file_path = default_storage.save(file_path, file_content)

        ElectionDocument.objects.create(
            storage_key=stored_file_path,
            region=region,
            content_type="application/xml",
            file_type=self.file_type,
            size=size,
        )
