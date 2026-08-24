import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import django
from django.db import connection, connections, transaction
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.handlers import XmlEventHandler

from eml_import.utils.file_handler import BaseFileHandler


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


class FolderEMLImporter(BaseFileHandler):
    # Set once per worker process by FolderEMLImporter._import_file
    _WORKER_PARSER: XmlParser | None = None

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._parser = build_parser()

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
                self.logger.error(
                    f"\033[31mFailed importing {parser_type} file {path} with exception: {type(e).__name__} {e}\033[0m"
                )
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
        assert cls._WORKER_PARSER is not None, "Worker parser not initialized."

        binding, importer_cls = cls._DOCUMENT_TYPES[parser_type]
        path = Path(raw_path)

        eml = cls._WORKER_PARSER.from_path(path, binding)
        with transaction.atomic():
            importer_cls(eml, path).parse()

        return raw_path
