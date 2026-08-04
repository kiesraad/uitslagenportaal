import logging
from abc import ABC, abstractmethod
from pathlib import Path
from xml.etree import ElementTree as ET

from django.conf import settings
from django.utils import timezone
from pyeml_bindings import ElectionIdentifierStructureKr, Eml110a, Eml230, Eml510
from tqdm import tqdm
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig

from election.models import (
    Contest,
    Election,
    ElectionConfig,
    ElectionDocument,
    VoteCount,
    VoterTurnoutCount,
)
from mainsite.models import RegionCategory
from party.models import Candidate, Party
from region.models import Region


class EMLBaseImporter[T](ABC):
    eml_type = None

    def __init__(self, eml: T, file_path):
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
            date=election_identifier_object.election_date[0].value.to_date(),
        )
        self.election = election

    def parse(self):
        try:
            self._parse_data()
        except ElectionConfig.DoesNotExist:
            self.logger.warning("Election is not configured, skipping 110a data import")

    def _parse_party_candidate_votecounts(
        self, contest, region, items, party_by_name, candidate_by_key, vote_counts
    ) -> None:
        current_party = None
        for votes_item in items:
            if votes_item.affiliation_identifier and votes_item.affiliation_identifier.registered_name:
                # get party from pre-saved data
                current_party = party_by_name[votes_item.affiliation_identifier.registered_name]
                vote_counts.append(
                    VoteCount(
                        region=region,
                        contest=contest,
                        party=current_party,
                        result_level=VoteCount.RESULT_LEVEL_PARTY,
                        valid_votes=votes_item.valid_votes,
                        eml_type=self.eml_type,
                    )
                )
            if votes_item.candidate:
                assert current_party, "No party to tie candidate to, cannot parse"
                # get candidate from pre-saved data
                candidate = candidate_by_key[
                    (
                        current_party.id,
                        int(votes_item.candidate.candidate_identifier.id),
                    )
                ]
                vote_counts.append(
                    VoteCount(
                        region=region,
                        contest=contest,
                        party=current_party,
                        candidate=candidate,
                        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
                        valid_votes=votes_item.valid_votes,
                        eml_type=self.eml_type,
                    )
                )

    def _collect_turnout_counts(self, contest, region, votes, turnout_counts) -> None:
        for rejected in votes.rejected_votes:
            turnout_counts.append(
                VoterTurnoutCount(
                    contest=contest,
                    region=region,
                    category=VoterTurnoutCount.CATEGORY_REJECTED,
                    reason_code=rejected.reason_code.value,
                    votes=rejected.value,
                )
            )
        for uncounted in votes.uncounted_votes:
            turnout_counts.append(
                VoterTurnoutCount(
                    contest=contest,
                    region=region,
                    category=VoterTurnoutCount.CATEGORY_UNCOUNTED,
                    reason_code=uncounted.reason_code.value,
                    votes=uncounted.value,
                )
            )
        turnout_counts.append(
            VoterTurnoutCount(
                contest=contest,
                region=region,
                category=VoterTurnoutCount.CATEGORY_TOTALS,
                reason_code="cast",
                votes=votes.cast,
            )
        )
        turnout_counts.append(
            VoterTurnoutCount(
                contest=contest,
                region=region,
                category=VoterTurnoutCount.CATEGORY_TOTALS,
                reason_code="total counted",
                votes=votes.total_counted,
            )
        )


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
            )

    def _parse_registered_parties(self) -> None:
        party_nodes = self.eml.election_event.election.registered_parties.registered_party
        for node in party_nodes:
            Party.objects.get_or_create(
                election=self.election,
                registered_name=node.registered_appellation.value,
            )


class EML230bImporter(EMLBaseImporter[Eml230]):
    """Kandidatenlijst"""

    def _get_election_identifier_data(self):
        return self.eml.candidate_list.election.election_identifier

    def _parse_data(self):
        assert len(self.eml.candidate_list.election.contest) == 1, "More than one contest, cannot parse"
        contest_data = self.eml.candidate_list.election.contest[0]
        contest, _ = Contest.objects.get_or_create(
            identifier=contest_data.contest_identifier.id,
            election=self.election,
        )
        for affiliation in contest_data.affiliation:
            try:
                party = Party.objects.get(
                    election=self.election,
                    registered_name=affiliation.affiliation_identifier.registered_name,
                )
            except Party.DoesNotExist:
                continue

            for candidate in affiliation.candidate:
                first_name = None
                if candidate.candidate_full_name.person_name.first_name:
                    first_name = candidate.candidate_full_name.person_name.first_name.content[0]
                name_prefix = None
                if candidate.candidate_full_name.person_name.name_prefix:
                    name_prefix = candidate.candidate_full_name.person_name.name_prefix.content[0]
                Candidate.objects.create(
                    party=party,
                    contest=contest,
                    identifier=candidate.candidate_identifier.id,
                    position=candidate.candidate_identifier.id,
                    initials=candidate.candidate_full_name.person_name.name_line.content[0],
                    first_name=first_name,
                    name_prefix=name_prefix,
                    last_name=candidate.candidate_full_name.person_name.last_name.content[0],
                )


class EML510bImporter(EMLBaseImporter[Eml510]):
    """Telling"""

    eml_type = "510b"

    def _get_election_identifier_data(self):
        return self.eml.count.election.election_identifier

    def _parse_data(self) -> None:
        authority_el = self.eml.managing_authority.authority_identifier
        managing_authority_name = (authority_el.value or "").strip()

        try:
            region = Region.objects.get(
                election=self.election,
                region_number=int(self.eml.managing_authority.authority_identifier.id),
                region_name=managing_authority_name,
            )
            ElectionDocument.objects.create(
                storage_key=self.file_path.relative_to(f"{settings.BASE_DIR}/.data").as_posix(),
                region=region,
                content_type="application/xml",
                size=len(self.file_path.read_bytes()),
                file_type=ElectionDocument.FILE_TYPE_EML510B,
            )
            region.results_available_at = timezone.now()
            region.save()

        except Region.DoesNotExist:
            # Municipality does not exist in the election definition, so we shouldn't import it's results
            return

        # Preload party names dict
        party_by_name = {party.registered_name: party for party in Party.objects.filter(election=self.election)}

        vote_counts: list[VoteCount] = []
        turnout_counts: list[VoterTurnoutCount] = []
        for contest_data in self.eml.count.election.contests.contest:
            contest = Contest.objects.get(
                identifier=contest_data.contest_identifier.id,
                election=self.election,
            )
            candidate_by_key = {
                (candidate.party_id, candidate.identifier): candidate
                for candidate in Candidate.objects.filter(contest=contest)
            }
            self._parse_party_candidate_votecounts(
                contest,
                region,
                contest_data.total_votes.selection,
                party_by_name,
                candidate_by_key,
                vote_counts,
            )
            self._collect_turnout_counts(contest, region, contest_data.total_votes, turnout_counts)
            for unit in contest_data.reporting_unit_votes:
                polling_station_name = unit.reporting_unit_identifier.value.split(" (postcode:")[0]
                # Strip leading Stembureau if present, do recursively for
                # eg 'Stembureau Stembureau Nutsgebouw Zwammerdam'
                while polling_station_name.startswith("Stembureau "):
                    polling_station_name = polling_station_name[len("Stembureau ") :]

                polling_station = Region.objects.create(
                    election=self.election,
                    region_number=unit.reporting_unit_identifier.id,
                    region_name=polling_station_name,
                    parent=region,
                    region_category=RegionCategory.STEMBUREAU,
                )
                self._parse_party_candidate_votecounts(
                    contest,
                    polling_station,
                    unit.selection,
                    party_by_name,
                    candidate_by_key,
                    vote_counts,
                )
                self._collect_turnout_counts(contest, polling_station, unit, turnout_counts)

        if vote_counts:
            VoteCount.objects.bulk_create(vote_counts, batch_size=4000)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=4000)


class EML510dImporter(EMLBaseImporter[Eml510]):
    """Totaaltelling."""

    eml_type = "510d"

    def _get_election_identifier_data(self):
        return self.eml.count.election.election_identifier

    def _parse_data(self) -> None:
        election_domain = self._get_election_identifier_data().election_domain
        if not isinstance(election_domain, list):
            election_domain = [election_domain]
        assert len(election_domain) == 1, "More than one election domain, cannot parse"
        region_number = int(election_domain[0].id) if election_domain[0].id else None
        region_name = election_domain[0].value
        if not region_number:
            # Allow for the case when the election domain has no region number attached,
            # this is the case in PS and region number is in that case not needed for retrieval
            region = Region.objects.get(
                election=self.election,
                # region_category=RegionCategory.WATERSCHAP,
                region_name=region_name,
            )
        else:
            region = Region.objects.get(
                election=self.election,
                # region_category=RegionCategory.WATERSCHAP,
                region_number=region_number,
                region_name=region_name,
            )

        # Preload party names dict
        party_by_name = {party.registered_name: party for party in Party.objects.filter(election=self.election)}

        gsb_by_name = {
            region.region_name: region
            for region in Region.objects.filter(election=self.election, region_category=RegionCategory.GEMEENTE)
        }

        vote_counts: list[VoteCount] = []
        turnout_counts: list[VoterTurnoutCount] = []
        for contest_data in self.eml.count.election.contests.contest:
            contest = Contest.objects.get(
                identifier=contest_data.contest_identifier.id,
                election=self.election,
            )
            candidate_by_key = {
                (candidate.party_id, candidate.identifier): candidate
                for candidate in Candidate.objects.filter(contest=contest)
            }
            # CSB totals
            self._parse_party_candidate_votecounts(
                contest,
                region,
                contest_data.total_votes.selection,
                party_by_name,
                candidate_by_key,
                vote_counts,
            )
            self._collect_turnout_counts(contest, region, contest_data.total_votes, turnout_counts)

            # Breakdown per GSB
            for unit in contest_data.reporting_unit_votes:
                gsb_name = unit.reporting_unit_identifier.value
                gsb_region = gsb_by_name.get(gsb_name)
                if gsb_region is None:
                    # GSB does not exist in the current election, skip import of data
                    continue

                self._parse_party_candidate_votecounts(
                    contest,
                    gsb_region,
                    unit.selection,
                    party_by_name,
                    candidate_by_key,
                    vote_counts,
                )
                self._collect_turnout_counts(contest, gsb_region, unit, turnout_counts)

        if vote_counts:
            VoteCount.objects.bulk_create(vote_counts, batch_size=1000)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=1000)


class ElectionImporter:
    def __init__(self, folder: Path):
        self.folder = folder

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._region_map: dict[tuple[str, str], Region] = {}
        self._parser = XmlParser(ParserConfig(fail_on_unknown_properties=True))

    _DOCUMENT_TYPES = {
        "110a": (Eml110a, EML110aImporter),  # Verkiezingsdefinitie
        "230b": (Eml230, EML230bImporter),  # Kandidatenlijst
        "510b": (Eml510, EML510bImporter),  # Telling
        "510d": (Eml510, EML510dImporter),  # Totaaltelling
    }

    @staticmethod
    def _document_id(xml_file_path: Path) -> str | None:
        for _, element in ET.iterparse(xml_file_path, events=("start",)):
            return element.get("Id")
        return None

    def _import_files(self, parser_type: str, xml_files: list[Path]) -> None:
        binding, importer_cls = self._DOCUMENT_TYPES[parser_type]
        files_str = ", ".join([str(path) for path in xml_files])
        self.logger.info(f"Importing {parser_type} files {files_str} using {importer_cls.__name__}...")
        for xml_file_path in tqdm(
            xml_files,
            desc="Processing XML",
            ncols=100,
            dynamic_ncols=False,
            bar_format="{l_bar}{bar:40}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ):
            eml = self._parser.from_path(xml_file_path, binding)
            importer_cls(eml, xml_file_path).parse()

    def _classify_files(self) -> dict[str, list[Path]]:
        xml_files: dict[str, list[Path]] = {key: [] for key in self._DOCUMENT_TYPES}
        for xml_file_path in sorted(self.folder.rglob("*.xml")):
            document_id = self._document_id(xml_file_path)
            if document_id in xml_files:
                xml_files[document_id].append(xml_file_path)
        return xml_files

    def run(self) -> None:
        xml_files = self._classify_files()
        for parser_type in self._DOCUMENT_TYPES:
            self._import_files(parser_type, xml_files[parser_type])
