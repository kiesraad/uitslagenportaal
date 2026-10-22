from django.db import transaction
from pyeml_bindings import (
    Eml110a,
)

from election.models import Contest, ElectionDocument
from eml_import.exceptions import EMLImporterException
from eml_import.utils.eml_base_importer import EMLBaseImporter
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.models import Party
from region.models import Region


class EML110aImporter(EMLBaseImporter[Eml110a]):
    """Verkiezingsdefinitie"""

    eml_type = EmlType.EML_110a
    file_type = ElectionDocument.FileType.EML_110A

    def _get_election_identifier_data(self):
        return self.eml.election_event.election.election_identifier

    def _parse_data(self):
        with transaction.atomic():
            if self._is_correction():
                self._ensure_exchange_correction_allowed()
                self._ensure_contest_unchanged()
            self._parse_contest()
            self._parse_regions()
            self._parse_registered_parties()
        self.logger.info("Successfully imported data for Election")

    def _is_correction(self) -> bool:
        if Contest.objects.filter(election=self.election).exists():
            self.logger.info(
                "\033[32mCorrection detected for election '%s', eml_type: %s\033[0m",
                self.election.name,
                self.eml_type,
            )
            return True
        return False

    def _ensure_contest_unchanged(self) -> None:
        """Reject a correction that changes the contest identifier: that restructures the election."""
        identifier = self.eml.election_event.election.contest.contest_identifier.id
        if not Contest.objects.filter(election=self.election, identifier=identifier).exists():
            raise EMLImporterException(
                f"Cannot correct {self.eml_type} for election {self.election.name}: contest '{identifier}' differs "
                "from the imported definition"
            )

    def _parse_contest(self) -> None:
        """
        Parse the contest from the election definition; only the top-level contest is defined here, which has a name
        of something like "alle" or "geen", depending on the election.
        """
        Contest.objects.get_or_create(
            identifier=self.eml.election_event.election.contest.contest_identifier.id,
            election=self.election,
            # The 230 may have named the contest since, so a correction leaves the name alone
            defaults={"name": self.eml.election_event.election.contest.contest_identifier.contest_name},
        )

    def _parse_regions(self) -> None:
        imported_ids = []
        for node in self.eml.election_event.election.election_tree.region:
            parent_region = None
            # A TK kieskring names only the category of its superior: the staat has no region number.
            if node.superior_region_category:
                parent_region = Region.objects.get(
                    election=self.election,
                    region_category=node.superior_region_category.value,
                    region_number=node.superior_region_number,
                )
            region, _ = Region.objects.update_or_create(
                election=self.election,
                region_category=node.region_category.value,
                region_number=node.region_number,
                defaults={
                    "parent": parent_region,
                    "region_name": node.region_name.value,
                    "csb": self._csb_for_parent(parent_region),
                },
            )
            imported_ids.append(region.pk)

        # Stembureaus come from the 510 counts, not from the election tree.
        Region.objects.filter(election=self.election).exclude(region_category=RegionCategory.STEMBUREAU).exclude(
            pk__in=imported_ids
        ).delete()

    def _parse_registered_parties(self) -> None:
        party_nodes = self.eml.election_event.election.registered_parties.registered_party
        existing_parties = set(Party.objects.filter(election=self.election).values_list("registered_name", flat=True))
        new_parties = {n.registered_appellation.value for n in party_nodes}
        parties_to_delete = existing_parties - new_parties

        for node in party_nodes:
            Party.objects.get_or_create(
                election=self.election,
                registered_name=node.registered_appellation.value,
            )

        Party.objects.filter(election=self.election, registered_name__in=parties_to_delete).delete()
