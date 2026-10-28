from pathlib import Path
from xml.etree import ElementTree as ET

from django.db import transaction
from pyeml_bindings import Eml110a

from election.models import Contest, Election, ElectionDocument
from eml_import.exceptions import EMLImporterException
from eml_import.utils.base_importer import BaseImporter
from eml_import.utils.eml_510_importer import normalise_postal_code
from eml_import.utils.eml_base_importer import EMLBaseImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from region.models import Region, build_region_slug


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
                    # save() only fills an empty slug, so a correction that renames the region sets it here
                    "slug": build_region_slug(node.region_number, node.region_name.value),
                    "csb": self._csb_for_parent(parent_region),
                },
            )
            imported_ids.append(region.pk)

        Region.objects.filter(election=self.election, region_category__in=self.TREE_CATEGORIES).exclude(
            pk__in=imported_ids
        ).delete()


EML_NS = {"eml": "urn:oasis:names:tc:evs:schema:eml", "xal": "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0"}


class EML110bImporter(BaseImporter):
    """Stembureaus. Read with ElementTree: pyeml_bindings has no 110b binding."""

    eml_type = EmlType.EML_110b
    file_type = ElectionDocument.FileType.EML_110B

    def __init__(self, file_path: Path | NamedBytesIO, *args, **kwargs):
        super().__init__(file_path, *args, **kwargs)
        if isinstance(file_path, NamedBytesIO):
            file_path.seek(0)
        self.root = ET.parse(file_path).getroot()
        self.election = self._find_election()

    def _find_election(self) -> Election:
        identifier = self.root.find("eml:ElectionEvent/eml:Election/eml:ElectionIdentifier", EML_NS)
        name = identifier.findtext("eml:ElectionName", namespaces=EML_NS)
        try:
            return Election.objects.get(election_config__identifier=identifier.get("Id").split("_")[0], name=name)
        except Election.DoesNotExist:
            raise EMLImporterException(f"Election {name} does not exist")

    def _parse_data(self) -> None:
        authority = self.root.find("eml:ManagingAuthority/eml:AuthorityIdentifier", EML_NS)
        authority_id = authority.get("Id")
        authority_name = (authority.text or "").strip()
        try:
            municipality = Region.objects.get(
                election=self.election, region_number=int(authority_id), region_name=authority_name
            )
        except Region.DoesNotExist:
            raise EMLImporterException(
                f"Municipality {authority_name} {authority_id} "
                f"does not exist in the election definition of election {self.election.name}"
            )

        existing = set(
            Region.objects.filter(
                election=self.election, parent=municipality, region_category=RegionCategory.STEMBUREAU
            ).values_list("region_number", flat=True)
        )
        csb = EMLBaseImporter._csb_for_parent(municipality)
        stations = []
        for location in self.root.iterfind(".//eml:PollingPlace/eml:PhysicalLocation", EML_NS):
            # Same number as the 510b ReportingUnitIdentifier, e.g. "0096::SB1"
            region_number = f"{authority_id}::SB{location.find('eml:PollingStation', EML_NS).get('Id')}"
            if region_number in existing:
                continue
            locality = location.find("eml:Address/eml:Locality", EML_NS)
            if locality is None:
                raise EMLImporterException(f"Stembureau {region_number} has no Locality address")
            region_name = locality.findtext("xal:LocalityName", default="", namespaces=EML_NS).strip()
            stations.append(
                Region(
                    election=self.election,
                    region_number=region_number,
                    region_name=region_name,
                    postal_code=normalise_postal_code(
                        locality.findtext("xal:PostalCode/xal:PostalCodeNumber", default="", namespaces=EML_NS)
                    ),
                    parent=municipality,
                    csb=csb,
                    region_category=RegionCategory.STEMBUREAU,
                    # bulk_create bypasses Region.save(), so derive the slug here
                    slug=build_region_slug(region_number, region_name),
                )
            )
        Region.objects.bulk_create(stations)
