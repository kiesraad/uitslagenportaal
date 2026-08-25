import logging
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

from eml_import.utils.eml_110_importer import EML110aImporter
from eml_import.utils.eml_230_importer import EML230bImporter
from eml_import.utils.eml_510_importer import EML510bImporter, EML510dImporter
from eml_import.utils.eml_base_importer import EMLBaseImporter
from mainsite.utils.eml_type import EmlType


def build_parser() -> XmlParser:
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


class BaseFileHandler:
    _DOCUMENT_TYPES: dict[str, tuple[type[Emlstructure], type[EMLBaseImporter]]] = {
        EmlType.EML_110a: (Eml110a, EML110aImporter),  # Verkiezingsdefinitie
        EmlType.EML_230b: (Eml230, EML230bImporter),  # Kandidatenlijst
        EmlType.EML_510b: (Eml510, EML510bImporter),  # Telling
        EmlType.EML_510d: (Eml510, EML510dImporter),  # Totaaltelling
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._parser = build_parser()

    @staticmethod
    def _root_element_id(source) -> str | None:
        # Only the root element is needed, so bail out on the first start event.
        for _, element in ET.iterparse(source, events=("start",)):
            return element.get("Id")
        return None

    @classmethod
    def _document_id(cls, xml_file_path: Path | BytesIO) -> str | None:
        if isinstance(xml_file_path, Path):
            # Open explicitly: returning early out of iterparse() otherwise leaves the
            # handle it opened for us to be closed by the GC, one per classified file.
            with xml_file_path.open("rb") as file_handle:
                return cls._root_element_id(file_handle)

        xml_file_path.seek(0)
        return cls._root_element_id(xml_file_path)

    def _classify_files[T = Path | BytesIO](self, input_files: list[T]) -> dict[str, list[T]]:
        xml_files: dict[str, list[T]] = {key: [] for key in self._DOCUMENT_TYPES}
        for xml_file_path in input_files:
            document_id = self._document_id(xml_file_path)
            if document_id and document_id in xml_files:
                xml_files[document_id].append(xml_file_path)
        return xml_files
