import logging
from abc import ABC, abstractmethod
from pathlib import Path

from election.models import ElectionConfig, ElectionDocument
from eml_import.models import ImportedEmlHash
from eml_import.utils.named_bytes_io import NamedBytesIO


class BaseImporter(ABC):
    file_type: ElectionDocument.FileType

    def __init__(self, file_path: Path | NamedBytesIO, *args, **kwargs):
        self.file_path = file_path
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def parse(self):
        if ImportedEmlHash.already_imported(self.file_path):
            self.logger.info(
                "\033[32mSkipping duplicate %s file %s\033[0m",
                self.file_type.value,
                self.file_path,
            )
            return
        try:
            self._parse_data()
        except ElectionConfig.DoesNotExist:
            self.logger.warning("Election is not configured, skipping %s data import", self.file_type.value)
        else:
            ImportedEmlHash.record(self.file_path)

    @abstractmethod
    def _parse_data(self): ...
