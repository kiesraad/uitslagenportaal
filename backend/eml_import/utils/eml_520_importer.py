import re
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from django.core.files.storage import default_storage
from django.utils import timezone

from election.models import Election, ElectionConfig, ElectionDocument
from eml_import.exceptions import EMLImporterException
from eml_import.utils.base_importer import BaseImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.utils.eml_type import EmlType
from region.models import Region


class EML520Importer(BaseImporter):
    """
    Store-only importer for EML 520 result files.

    No result data is imported; the file is only read to find the election and its CSB.
    """

    eml_type = EmlType.EML_520
    file_type = ElectionDocument.FileType.EML_520

    def __init__(self, file_path: Path | NamedBytesIO, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)
        self.election = self._find_election(self.file_path)

    def _parse_data(self):
        assert self.election is not None
        self._store_eml(self._find_csb(self.election))

    @classmethod
    def _find_election(cls, file_path: Path | NamedBytesIO) -> Election:
        identifier, name = cls._read_election_fields(file_path)
        if not identifier or not name:
            raise EMLImporterException("Not a valid EML 520 file")

        config_identifier = identifier.split("_")[0]
        try:
            election_config = ElectionConfig.with_expired.get(identifier=config_identifier)
        except ElectionConfig.DoesNotExist as ex:
            raise EMLImporterException(f"ElectionConfig does not exist for {config_identifier}") from ex

        try:
            return Election.objects.get(election_config=election_config, name=name)
        except Election.DoesNotExist as ex:
            raise EMLImporterException(f"Election {name} does not exist") from ex

    @staticmethod
    def _read_election_fields(file_path: Path | BytesIO) -> tuple[str | None, str | None]:
        """ElectionIdentifier/@Id and ElectionName, ignoring namespaces."""

        def read(source) -> tuple[str | None, str | None]:
            identifier = None
            name = None
            for event, element in ET.iterparse(source, events=("start", "end")):
                local = element.tag.rsplit("}", 1)[-1]
                if event == "start" and local == "ElectionIdentifier" and identifier is None:
                    identifier = element.get("Id")
                elif event == "end" and local == "ElectionName" and name is None:
                    name = (element.text or "").strip() or None
                if identifier and name:
                    return identifier, name
            return identifier, name

        if isinstance(file_path, Path):
            with file_path.open("rb") as file_handle:
                return read(file_handle)

        file_path.seek(0)
        try:
            return read(file_path)
        finally:
            file_path.seek(0)

    @staticmethod
    def _find_csb(election: Election) -> Region:
        try:
            return Region.objects.get(election=election, region_category=election.election_config.csb_type)
        except Region.DoesNotExist as ex:
            raise EMLImporterException(
                f"CSB region does not exist in the election definition of election {election.name}"
            ) from ex

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

        ElectionDocument.objects.filter(region=region, file_type=self.file_type).archive()
        ElectionDocument.objects.create(
            storage_key=stored_file_path,
            region=region,
            content_type="application/xml",
            file_type=self.file_type,
            size=size,
        )
