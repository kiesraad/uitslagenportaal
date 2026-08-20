import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from eml_import.utils.election_importer import FolderEMLImporter


def default_workers() -> int:
    return max(1, (os.cpu_count() or 1))


class FolderEMLIMporter(object):
    # TODO: this one goes out of this class
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


class Command(BaseCommand):
    help = "Import an election fixture folder into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "folder",
            type=str,
            help="Path to a fixture folder containing EML XML files.",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=default_workers(),
            help="Number of worker processes to import with (default: one per CPU). use 1 to import serially.",
        )

    def handle(self, *args, **options):
        folder = Path(options["folder"]).resolve()
        if not folder.is_dir():
            raise CommandError(f"Folder does not exist: {folder}")

        workers = options["workers"]
        if workers < 1:
            raise CommandError(f"--workers must be at least 1, got {workers}")

        start = time.time()
        FolderEMLImporter().import_folder(folder, workers=workers)
        self.stdout.write(self.style.SUCCESS(f"Processed {folder} in {time.time() - start:.1f} seconds"))
