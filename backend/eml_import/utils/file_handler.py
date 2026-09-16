import logging
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from pyeml_bindings import (
    Eml110a,
    Eml230,
    Eml510,
    Emlstructure,
)
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.handlers import XmlEventHandler

from eml_import.utils.base_importer import BaseImporter
from eml_import.utils.csv_osv43_importer import CSVOsv43Importer
from eml_import.utils.eml_110_importer import EML110aImporter
from eml_import.utils.eml_230_importer import EML230bImporter
from eml_import.utils.eml_510_importer import EML510bImporter, EML510cImporter, EML510dImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.eml_type import CsvType, EmlType


def build_xml_parser() -> XmlParser:
    """
    Build the shared xsdata parser.

    Pins the stdlib ElementTree handler: xsdata's default_handler() switches to
    LxmlEventHandler whenever lxml is merely importable, and that measured ~25%
    slower on GR2026 data.
    """
    return XmlParser(
        ParserConfig(fail_on_unknown_properties=True),
        handler=XmlEventHandler,
    )


class BaseFileHandler(ABC):
    _DOCUMENT_TYPES: dict[str, tuple[type[Emlstructure] | None, type[BaseImporter]]] = {
        EmlType.EML_110a: (Eml110a, EML110aImporter),  # Verkiezingsdefinitie
        EmlType.EML_230b: (Eml230, EML230bImporter),  # Kandidatenlijst
        EmlType.EML_510b: (Eml510, EML510bImporter),  # Telling
        EmlType.EML_510c: (Eml510, EML510cImporter),  # Telling HSB
        EmlType.EML_510d: (Eml510, EML510dImporter),  # Totaaltelling
        CsvType.CSV_OSV43: (None, CSVOsv43Importer),  # CSV telling
    }

    _VALID_EXTENSIONS = [".xml", ".csv"]

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._xml_parser = build_xml_parser()

    @staticmethod
    def _root_element_id(source) -> str | None:
        # Only the root element is needed, so bail out on the first start event.
        for _, element in ET.iterparse(source, events=("start",)):
            return element.get("Id")
        return None

    @classmethod
    def _eml_document_id(cls, xml_file_path: Path | BytesIO) -> str | None:
        if isinstance(xml_file_path, Path):
            # Open explicitly: returning early out of iterparse() otherwise leaves the
            # handle it opened for us to be closed by the GC, one per classified file.
            with xml_file_path.open("rb") as file_handle:
                return cls._root_element_id(file_handle)

        xml_file_path.seek(0)
        return cls._root_element_id(xml_file_path)

    def _classify_files[T: Path | NamedBytesIO](self, input_files: list[T]) -> dict[str, list[T]]:
        files: dict[str, list[T]] = {key: [] for key in self._DOCUMENT_TYPES}
        for file_path in input_files:
            match file_path.suffix:
                case ".xml":
                    document_id = self._eml_document_id(file_path)
                    if document_id and document_id in files:
                        files[document_id].append(file_path)
                case ".csv":
                    csv_header = CSVOsv43Importer.read_csv_header(file_path)
                    # OSV4-3 CSVs should contain a Verkiezing/Nummer header row
                    if {"Verkiezing", "Nummer"} <= set(csv_header.keys()):
                        files[CsvType.CSV_OSV43].append(file_path)
        return files

    @abstractmethod
    def run(self) -> tuple[int, bool]:
        """
        Run the file handler.
        :return: A tuple of [number of processed files, if work remains for the next run]
        """
