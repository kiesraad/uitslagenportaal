from io import BytesIO
from pathlib import Path


class BaseFileHandler:
    def _classify_files[T = Path | BytesIO](self, input_files: list[T]) -> dict[str, list[T]]:
        xml_files: dict[str, list[T]] = {key: [] for key in self._DOCUMENT_TYPES}
        for xml_file_path in input_files:
            document_id = self._document_id(xml_file_path)
            if document_id and document_id in xml_files:
                xml_files[document_id].append(xml_file_path)
        return xml_files
