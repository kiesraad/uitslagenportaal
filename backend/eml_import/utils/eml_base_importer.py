import logging
from abc import ABC, abstractmethod
from pathlib import Path

from pyeml_bindings import (
    ElectionIdentifierStructureKr,
)

from election.models import (
    Election,
    ElectionConfig,
)
from region.models import Region


class EMLBaseImporter[T](ABC):
    BLANCO_PARTY_REGISTERED_NAME = "Blanco Lijst"
    BULK_BATCH_SIZE = 4000

    eml_type = None

    def __init__(self, eml: T, file_path: Path | None):
        self.eml = eml
        self.file_path = file_path

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.election_config = None
        self.linked_region = None
        self._parse_election()

    @abstractmethod
    def _get_election_identifier_data(self) -> ElectionIdentifierStructureKr: ...

    @abstractmethod
    def _parse_data(self): ...

    def _parse_election(self) -> None:
        election_identifier = self._get_election_identifier_data().id.split("_")[0]
        self.election_config = ElectionConfig.objects.get(identifier=election_identifier)
        election_identifier_object = self._get_election_identifier_data()
        election, _ = Election.objects.get_or_create(
            election_config=self.election_config,
            name=election_identifier_object.election_name,
            subcategory=election_identifier_object.election_subcategory[0].value.value,
            defaults={
                # Date can differ between files, e.g. when there was a re-election (Gorinchem GR2026)
                "date": election_identifier_object.election_date[0].value.to_date(),
            },
        )
        self.election = election

    def parse(self):
        try:
            self._parse_data()
        except ElectionConfig.DoesNotExist:
            self.logger.warning("Election is not configured, skipping 110a data import")

    @staticmethod
    def _csb_for_parent(parent: Region | None) -> Region | None:
        """
        CSB is the election-tree root.

        Root regions have no parent and no csb. Children inherit the parent's csb,
        or the parent itself when the parent is the root.
        """
        if parent is None:
            return None
        return parent.csb or parent
