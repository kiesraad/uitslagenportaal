
from pyeml_bindings import (
    Eml110a,
)

from eml_import.utils.eml_base_importer import EMLBaseImporter
from party.models import Party
from region.models import Region


class EML110aImporter(EMLBaseImporter[Eml110a]):
    """Verkiezingsdefinitie"""

    def _get_election_identifier_data(self):
        return self.eml.election_event.election.election_identifier

    def _parse_data(self):
        self._parse_regions()
        self._parse_registered_parties()
        self.logger.info("Successfully imported data for Election")

    def _parse_regions(self) -> None:
        region_nodes = self.eml.election_event.election.election_tree.region
        for node in region_nodes:
            parent_region = None
            if node.superior_region_number:
                parent_region = Region.objects.get(
                    election=self.election,
                    region_category=node.superior_region_category.value,
                    region_number=node.superior_region_number,
                )
            Region.objects.update_or_create(
                election=self.election,
                parent=parent_region,
                region_name=node.region_name.value,
                region_category=node.region_category.value,
                region_number=node.region_number,
                defaults={"csb": self._csb_for_parent(parent_region)},
            )

    def _parse_registered_parties(self) -> None:
        party_nodes = self.eml.election_event.election.registered_parties.registered_party
        for node in party_nodes:
            Party.objects.get_or_create(
                election=self.election,
                registered_name=node.registered_appellation.value,
            )
