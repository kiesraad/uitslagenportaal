from pyeml_bindings import Eml520

from election.models import Election, ElectionDocument
from eml_import.exceptions import EMLImporterException
from eml_import.utils.base_importer import EMLStorageMixin
from eml_import.utils.eml_base_importer import EMLBaseImporter
from mainsite.utils.eml_type import EmlType
from region.models import Region


class EML520Importer(EMLStorageMixin, EMLBaseImporter[Eml520]):
    """
    Store-only importer for EML 520 result files.

    No result data is imported; the file is only stored as a document of the election's CSB.
    """

    eml_type = EmlType.EML_520
    file_type = ElectionDocument.FileType.EML_520

    def _get_election_identifier_data(self):
        return self.eml.result.election.election_identifier

    def _parse_data(self):
        region = self._find_csb(self.election)
        ElectionDocument.objects.filter(region=region, file_type=self.file_type).archive()
        self._store_eml(region)

    @staticmethod
    def _find_csb(election: Election) -> Region:
        try:
            return Region.objects.get(election=election, region_category=election.election_config.csb_type)
        except Region.DoesNotExist as ex:
            raise EMLImporterException(
                f"CSB region does not exist in the election definition of election {election.name}"
            ) from ex
