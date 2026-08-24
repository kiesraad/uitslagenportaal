from django.db import transaction
from pyeml_bindings import (
    Eml110a,
)

from eml_import.utils.eml_base_importer import EMLBaseImporter
from mainsite.utils.eml_type import EmlType
from party.models import Party
from region.models import Region


class EML110aImporter(EMLBaseImporter[Eml110a]):
    """Verkiezingsdefinitie"""

    eml_type = EmlType.EML_110a

    def _get_election_identifier_data(self):
        return self.eml.election_event.election.election_identifier

    def _parse_data(self):
        with transaction.atomic():
            if self._is_correction():
                self._ensure_exchange_correction_allowed()
                self._archive()
            self._parse_regions()
            self._parse_registered_parties()
        self.logger.info("Successfully imported data for Election")

    def _is_correction(self) -> bool:
        if Region.objects.filter(election=self.election).exists():
            self.logger.info(
                "\033[32mCorrection detected for election %s eml_type=%s\033[0m",
                self.election.name,
                self.eml_type,
            )
            return True
        return False

    def _archive(self) -> None:
        """
        Archive the previous UIT-derived tree for this election so a corrected 110a
        can recreate contests, regions and parties.
        """
        Party.objects.filter(election=self.election).archive()
        Region.objects.filter(election=self.election).archive()

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
