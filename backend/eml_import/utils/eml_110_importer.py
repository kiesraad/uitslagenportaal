from django.db import transaction
from pyeml_bindings import (
    Eml110a,
)

from election.models import Contest, ElectionDocument
from eml_import.exceptions import EMLImporterException
from eml_import.utils.eml_base_importer import EMLBaseImporter
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from region.models import Region


class EML110aImporter(EMLBaseImporter[Eml110a]):
    """Verkiezingsdefinitie"""

    eml_type = EmlType.EML_110a
    file_type = ElectionDocument.FileType.EML_110A

    # The regions of the election tree; stembureaus come from the 510 counts.
    TREE_CATEGORIES = (
        RegionCategory.STAAT,
        RegionCategory.WATERSCHAP,
        RegionCategory.PROVINCIE,
        RegionCategory.KIESKRING,
        RegionCategory.GEMEENTE,
    )

    def _get_election_identifier_data(self):
        return self.eml.election_event.election.election_identifier

    def _parse_data(self):
        with transaction.atomic():
            if self._is_correction():
                self._ensure_exchange_correction_allowed()
                self._ensure_contest_unchanged()
            self._parse_contest()
            self._parse_regions()
            # RegisteredParties is left alone: it also lists parties that submitted no list. The 230b creates parties.
        self.logger.info("Successfully imported data for Election")

    def _is_correction(self) -> bool:
        # Only a 110a creates the election tree; a 230b also creates contests, but no regions.
        if Region.objects.filter(election=self.election, region_category__in=self.TREE_CATEGORIES).exists():
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

        Region.objects.filter(election=self.election, region_category__in=self.TREE_CATEGORIES).exclude(
            pk__in=imported_ids
        ).delete()
