import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import django
from django.db import connection, connections, transaction
from pyeml_bindings import (
    Eml110a,
    Eml230,
    Eml510,
    Emlstructure,
)
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.handlers import XmlEventHandler

from election.models import (
    VoteCount,
)
from eml_import.utils.eml_110_importer import EML110aImporter
from eml_import.utils.eml_230_importer import EML230bImporter
from eml_import.utils.eml_510_importer import EML510bImporter, EML510dImporter
from eml_import.utils.eml_base_importer import EMLBaseImporter
from eml_import.utils.named_bytes_io import NamedBytesIO


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


class ElectionImporter:
    # Set once per worker process by ElectionImporter._import_file
    _WORKER_PARSER: XmlParser | None = None

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._parser = build_parser()

    _DOCUMENT_TYPES: dict[str, tuple[type[Emlstructure], type[EMLBaseImporter]]] = {
        "110a": (Eml110a, EML110aImporter),  # Verkiezingsdefinitie
        "230b": (Eml230, EML230bImporter),  # Kandidatenlijst
        VoteCount.EML_TYPE_510B: (Eml510, EML510bImporter),  # Telling
        VoteCount.EML_TYPE_510D: (Eml510, EML510dImporter),  # Totaaltelling
    }

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

    def _process_file_paths(self, parser_type: str, xml_files: list[Path]) -> None:
        """
        Process the list of paths of `xml_files` using the parser for `parser_type`
        """
        binding, importer_cls = self._DOCUMENT_TYPES[parser_type]
        self.logger.info(f"Importing {parser_type} files using {importer_cls.__name__}...")
        file_cnt = len(xml_files)
        for i, xml_file_path in enumerate(xml_files, start=1):
            self.logger.info(f"Processing [{i}/{file_cnt}] {xml_file_path}...")
            eml = self._parser.from_path(xml_file_path, binding)
            # Use a transaction to prevent auto-commit round-trips for each insert query
            try:
                with transaction.atomic():
                    importer_cls(eml, xml_file_path).parse()
            except Exception as e:
                self.logger.error(
                    f"Failed importing {parser_type} file {xml_file_path} with exception: {type(e).__name__} {e}"
                )

    def _classify_files[T = Path | BytesIO](self, input_files: list[T]) -> dict[str, list[T]]:
        xml_files: dict[str, list[T]] = {key: [] for key in self._DOCUMENT_TYPES}
        for xml_file_path in input_files:
            document_id = self._document_id(xml_file_path)
            if document_id and document_id in xml_files:
                xml_files[document_id].append(xml_file_path)
        return xml_files

    def import_folder(self, folder: Path, workers: int = 1) -> None:
        """
        Import all XML files from the given folder.

        With `workers` > 1 the files of each document type are imported
        concurrently. The document types themselves stay sequential.
        """
        files = sorted(folder.rglob("*.xml"))
        xml_files = self._classify_files(files)

        workers = self._usable_workers(workers)
        if workers == 1:
            for parser_type in self._DOCUMENT_TYPES:
                self._process_file_paths(parser_type, xml_files[parser_type])
            return

        # Hand no open connection to the children, and force "spawn" so a forked
        # child can never inherit this process's socket.
        connections.close_all()
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=django.setup,
        ) as pool:
            for parser_type in self._DOCUMENT_TYPES:
                # Each phase is a barrier: _process_file_paths_parallel does not
                # return until every file of this document type is imported.
                self._process_file_paths_parallel(pool, parser_type, xml_files[parser_type], workers)

    def _usable_workers(self, workers: int) -> int:
        """Refuse to spawn workers when they could not see the caller's data."""
        if workers > 1 and connection.in_atomic_block:
            # Worker processes get their own connections, so they cannot see rows
            # written inside the caller's still-open transaction (this is exactly
            # the case under pytest's django_db, which also renames the database).
            self.logger.warning(
                "Called inside an open transaction; importing serially instead of with %s workers.",
                workers,
            )
            return 1
        return workers

    def _process_file_paths_parallel(
        self,
        pool: ProcessPoolExecutor,
        parser_type: str,
        xml_files: list[Path],
        workers: int,
    ) -> None:
        """
        Import one document type on `pool`, one file per task, largest file first.
        """
        if not xml_files:
            return

        ordered = sorted(xml_files, key=lambda path: path.stat().st_size, reverse=True)

        _, importer_cls = self._DOCUMENT_TYPES[parser_type]
        self.logger.info(
            f"Importing {len(ordered)} {parser_type} files using {importer_cls.__name__} across {workers} workers..."
        )

        done = 0
        futures = {pool.submit(self._import_file, parser_type, str(path)): path for path in ordered}
        for future in as_completed(futures):
            path = futures[future]
            try:
                processed_path = future.result()
                done += 1
                self.logger.info(f"[{done}/{len(ordered)}] Processed {parser_type} file {processed_path}...")
            except Exception as e:
                # With any error the importer should continue as to not have everything fail
                self.logger.error(f"Failed importing {parser_type} file {path} with exception: {type(e).__name__} {e}")
                continue

    @classmethod
    def _import_file(cls, parser_type: str, raw_path: str) -> str:
        """
        Parse and import a single EML file. Runs in a worker process.

        One task per file: the importers scope their writes to the region named by
        the file (its managing authority), so files of the same document type do
        not touch each other's rows even when they belong to one nationwide
        election.
        """
        if cls._WORKER_PARSER is None:
            # Once per worker process, not once per file.
            cls._WORKER_PARSER = build_parser()

        binding, importer_cls = cls._DOCUMENT_TYPES[parser_type]
        path = Path(raw_path)

        eml = cls._WORKER_PARSER.from_path(path, binding)
        with transaction.atomic():
            importer_cls(eml, path).parse()

        return raw_path

    def import_file_objects(self, files: list[NamedBytesIO]) -> None:
        """
        Import all given file-like objects.
        """
        xml_files = self._classify_files(files)
        for parser_type, (binding, importer_cls) in self._DOCUMENT_TYPES.items():
            for file in xml_files[parser_type]:
                self.logger.info(f"Importing {parser_type} file {file.filename}")
                eml = self._parser.from_bytes(file.getvalue(), binding)
                try:
                    with transaction.atomic():
                        importer_cls(eml, None).parse()
                except Exception as e:
                    self.logger.error(
                        f"Failed importing {parser_type} file {file.filename} with exception: {type(e).__name__} {e}"
                    )
