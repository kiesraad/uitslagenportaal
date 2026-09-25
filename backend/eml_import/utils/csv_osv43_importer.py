import csv
import io
import re
from io import BytesIO
from itertools import islice
from pathlib import Path
from typing import IO

from django.core.files.storage import default_storage
from django.utils import timezone

from election.models import Election, ElectionConfig, ElectionDocument
from eml_import.exceptions import EMLImporterException
from eml_import.utils.base_importer import BaseImporter
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import CsvType
from region.models import Region

HSB_NUMBER_RE = re.compile(r"HSB(\d+)")
REGION_NAME_PREFIX_RE = re.compile(r"^(Gemeente|Kieskring|Openbaar lichaam) ")


class CSVOsv43Importer(BaseImporter):
    """
    Importer for OSV4-3 CSV files.
    No data is imported from these files, the file is only parsed to determine for which election/region to store it.
    """

    csv_type: CsvType = CsvType.CSV_OSV43
    file_type = ElectionDocument.FileType.CSV_OSV43

    @staticmethod
    def read_csv_header(file_path: Path | BytesIO) -> dict[str, str]:
        """Reads the header block from an OSV4-3 CSV."""

        def read_header(f: IO) -> dict[str, str]:
            headers = {}
            for row in islice(csv.reader(f, delimiter=";"), 10):
                # Filter out empty cells
                row = [c for c in row if c]
                if len(row) < 2:
                    # Header block ends with empty row
                    break
                headers[row[0]] = row[-1]
            return headers

        if isinstance(file_path, Path):
            with file_path.open("r", newline="", encoding="utf-8-sig") as file_handle:
                return read_header(file_handle)

        file_path.seek(0)
        wrapper = io.TextIOWrapper(file_path, encoding="utf-8-sig", newline="")
        try:
            return read_header(wrapper)
        finally:
            # Detach, or the wrapper closes the underlying buffer when it is garbage-collected
            wrapper.detach()
            file_path.seek(0)

    def _parse_data(self):
        csv_headers = self.read_csv_header(self.file_path)
        if not {"Verkiezing", "Nummer", "Gebied"} <= csv_headers.keys():
            raise EMLImporterException("Not a valid OSV4-3 CSV file")

        election = self._find_election(csv_headers)
        region = self._find_region(election, csv_headers)

        self._store_csv(election.election_config, region)

    @staticmethod
    def _find_election(csv_headers: dict[str, str]) -> Election:
        election_name = csv_headers["Verkiezing"]
        try:
            return Election.objects.get(name=election_name)
        except Election.DoesNotExist:
            raise EMLImporterException(f"Election {election_name} does not exist")

    @staticmethod
    def _find_region(election: Election, csv_headers: dict[str, str]) -> Region:
        """
        Find the region from the 'Nummer' and 'Gebied' header rows.

        'Nummer' is "CSB", "HSB<kieskring number>" or the CBS code of the gemeente, openbaar
        lichaam or NBSB. 'Gebied' is the region name, prefixed with its category in some
        elections (e.g. "Kieskring Zwolle" in TK, but just "Zwolle" in GR).
        """
        number = csv_headers["Nummer"]
        name = REGION_NAME_PREFIX_RE.sub("", csv_headers["Gebied"])

        regions = Region.objects.filter(election=election, region_name=name)
        if number == "CSB":
            # The CSB region has no number in TK, and the gemeente number in GR
            regions = regions.filter(region_category=election.election_config.csb_type)
        elif match := HSB_NUMBER_RE.fullmatch(number):
            regions = regions.filter(region_category=RegionCategory.KIESKRING, region_number=match[1])
        elif number.isdigit():
            regions = regions.filter(region_category=RegionCategory.GEMEENTE, region_number=str(int(number)))
        else:
            raise EMLImporterException(f"Unknown region number {number} for {name}")

        try:
            return regions.get()
        except Region.DoesNotExist:
            raise EMLImporterException(
                f"Region {name} ({number}) does not exist in the election definition of election {election.name}"
            )

    def _store_csv(self, election_config: ElectionConfig, region: Region) -> None:
        parent_number, parent_name = (
            (region.parent.region_number, region.parent.region_name) if region.parent else (None, None)
        )
        filename = "_".join(
            filter(
                lambda x: x,
                [
                    election_config.identifier,
                    self.csv_type.label,
                    parent_number,
                    parent_name,
                    region.region_number,
                    region.region_name,
                    timezone.now().isoformat(timespec="seconds"),
                ],
            )
        )
        filename = re.sub(r"[^A-Za-z0-9_\-:+]", "", filename.replace(" ", "_"))
        file_path = f"{election_config.identifier}/{filename}.csv"

        if isinstance(self.file_path, Path):
            file_content = BytesIO(self.file_path.read_bytes())
        else:
            file_content = self.file_path
        file_content.seek(0)
        size = len(file_content.getvalue())
        stored_file_path = default_storage.save(file_path, file_content)

        ElectionDocument.objects.filter(region=region, file_type=self.file_type).archive()

        ElectionDocument.objects.create(
            storage_key=stored_file_path,
            region=region,
            content_type="text/csv",
            file_type=self.file_type,
            size=size,
        )
