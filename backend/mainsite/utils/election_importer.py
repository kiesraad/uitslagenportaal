import logging
import multiprocessing
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import django
from django.conf import settings
from django.db import connection, connections, transaction
from django.utils import timezone
from pyeml_bindings import (
    Count,
    CountingMethodMethodCode,
    ElectionIdentifierStructureKr,
    Eml110a,
    Eml230,
    Eml510,
    Emlstructure,
    ReportingUnitVotes,
)
from xsdata.formats.dataclass.parsers import XmlParser
from xsdata.formats.dataclass.parsers.config import ParserConfig
from xsdata.formats.dataclass.parsers.handlers import XmlEventHandler

from election.models import (
    Contest,
    Election,
    ElectionConfig,
    ElectionDocument,
    VoteCount,
    VoterTurnoutCount,
)
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import CountingMethod, RegionCategory
from party.models import Candidate, Party
from region.models import Region, build_region_slug


def _csb_for_parent(parent: Region | None) -> Region | None:
    """
    CSB is the election-tree root.

    Root regions have no parent and no csb. Children inherit the parent's csb,
    or the parent itself when the parent is the root.
    """
    if parent is None:
        return None
    return parent.csb or parent


BLANCO_PARTY_REGISTERED_NAME = "Blanco Lijst"

# Shared by every bulk_create() in this module, so batching behaviour is uniform.
BULK_BATCH_SIZE = 4000


def build_parser() -> XmlParser:
    """
    Build the shared xsdata parser.

    Pins the stdlib ElementTree handler: xsdata's default_handler() switches to
    LxmlEventHandler whenever lxml is merely importable, and that measured ~25%
    slower on GR2026 data.

    Module-level so process-pool workers build an identical parser.
    """
    return XmlParser(
        ParserConfig(fail_on_unknown_properties=True),
        handler=XmlEventHandler,
    )


# Set once per worker process by ElectionImporter._import_file; unused in the parent,
# which uses its own ElectionImporter._parser.
_WORKER_PARSER: XmlParser | None = None


class EMLBaseImporter[T](ABC):
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
                defaults={"csb": _csb_for_parent(parent_region)},
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
        candidates: list[Candidate] = []
        for affiliation in contest_data.affiliation:
            assert affiliation.affiliation_identifier.id, (
                f"AffiliationIdentifier/@Id missing for party "
                f"{affiliation.affiliation_identifier.registered_name or BLANCO_PARTY_REGISTERED_NAME}"
            )
            list_number = int(affiliation.affiliation_identifier.id)
            try:
                party = Party.objects.get(
                    election=self.election,
                    registered_name=affiliation.affiliation_identifier.registered_name,
                )
                party.list_number = list_number
                party.save(update_fields=["list_number", "updated_at"])
            except Party.DoesNotExist:
                # Some candidates are not affiliated to any party
                party, _ = Party.objects.get_or_create(
                    election=self.election,
                    registered_name=f"{BLANCO_PARTY_REGISTERED_NAME} {list_number}",
                    list_number=list_number,
                )

            for candidate in affiliation.candidate:
                first_name = None
                if candidate.candidate_full_name.person_name.first_name:
                    first_name = candidate.candidate_full_name.person_name.first_name.content[0]
                name_prefix = None
                if candidate.candidate_full_name.person_name.name_prefix:
                    name_prefix = candidate.candidate_full_name.person_name.name_prefix.content[0]
                candidates.append(
                    Candidate(
                        party=party,
                        contest=contest,
                        identifier=candidate.candidate_identifier.id,
                        position=candidate.candidate_identifier.id,
                        initials=candidate.candidate_full_name.person_name.name_line.content[0],
                        first_name=first_name,
                        name_prefix=name_prefix,
                        last_name=candidate.candidate_full_name.person_name.last_name.content[0],
                    )
                )

        if candidates:
            Candidate.objects.bulk_create(candidates, batch_size=BULK_BATCH_SIZE)


class EML510BaseImporter(EMLBaseImporter[Eml510], ABC):
    @staticmethod
    def _counting_method(count) -> str | None:
        counting_method = getattr(count, "counting_method", None)
        if counting_method is None:
            return None
        return {
            CountingMethodMethodCode.CENTRALE_STEMOPNEMING: CountingMethod.CSO,
            CountingMethodMethodCode.DECENTRALE_STEMOPNEMING: CountingMethod.DSO,
        }.get(counting_method.method_code)

    def _parse_party_candidate_votecounts(
        self,
        contest,
        region,
        items: list[Count.Election.Contests.Contest.TotalVotes.Selection | ReportingUnitVotes.Selection],
        party_by_list_nuber: dict[int, Party],
        candidate_by_key,
        vote_counts,
    ) -> None:
        current_party = None
        for votes_item in items:
            if votes_item.affiliation_identifier:
                # get party from pre-saved data
                current_party = party_by_list_nuber[int(votes_item.affiliation_identifier.id)]
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
                try:
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
                except KeyError:
                    self.logger.error(
                        "Candidate %s not found within party %s",
                        int(votes_item.candidate.candidate_identifier.id),
                        current_party.registered_name,
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
                    eml_type=self.eml_type,
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
                    eml_type=self.eml_type,
                )
            )
        turnout_counts.append(
            VoterTurnoutCount(
                contest=contest,
                region=region,
                category=VoterTurnoutCount.CATEGORY_TOTALS,
                reason_code="cast",
                votes=votes.cast,
                eml_type=self.eml_type,
            )
        )
        turnout_counts.append(
            VoterTurnoutCount(
                contest=contest,
                region=region,
                category=VoterTurnoutCount.CATEGORY_TOTALS,
                reason_code="total counted",
                votes=votes.total_counted,
                eml_type=self.eml_type,
            )
        )


class EML510bImporter(EML510BaseImporter):
    """Telling"""

    eml_type = VoteCount.EML_TYPE_510B

    def _get_election_identifier_data(self):
        return self.eml.count.election.election_identifier

    @staticmethod
    def _polling_station_name(unit: ReportingUnitVotes) -> str:
        name = unit.reporting_unit_identifier.value.split(" (postcode:")[0]
        # Strip leading Stembureau if present, do recursively for
        # eg 'Stembureau Stembureau Nutsgebouw Zwammerdam'
        while name.startswith("Stembureau "):
            name = name[len("Stembureau ") :]
        return name

    def _ensure_polling_stations(self, region: Region) -> dict[tuple[str, str], Region]:
        """
        Create all polling stations of this file up front, keyed by (number, name).

        Replaces a per-station get_or_create (a SELECT plus an INSERT each, in the
        hottest loop of the import) with one SELECT, one bulk INSERT and one SELECT
        for the whole file.
        """
        stations_filter = {
            "election": self.election,
            "parent": region,
            "region_category": RegionCategory.STEMBUREAU,
        }
        existing = {
            (station.region_number, station.region_name): station
            for station in Region.objects.filter(**stations_filter)
        }

        wanted: set[tuple[str, str]] = set()
        for contest_data in self.eml.count.election.contests.contest:
            for unit in contest_data.reporting_unit_votes:
                wanted.add((str(unit.reporting_unit_identifier.id), self._polling_station_name(unit)))

        missing = wanted - existing.keys()
        if not missing:
            return existing

        csb = _csb_for_parent(region)
        Region.objects.bulk_create(
            [
                Region(
                    election=self.election,
                    region_number=region_number,
                    region_name=region_name,
                    parent=region,
                    csb=csb,
                    region_category=RegionCategory.STEMBUREAU,
                    # bulk_create bypasses Region.save(), so derive the slug here
                    slug=build_region_slug(region_number, region_name),
                )
                for region_number, region_name in missing
            ],
            batch_size=BULK_BATCH_SIZE,
        )

        return {
            (station.region_number, station.region_name): station
            for station in Region.objects.filter(**stations_filter)
        }

    def _parse_data(self) -> None:
        authority_el = self.eml.managing_authority.authority_identifier
        managing_authority_name = (authority_el.value or "").strip()

        try:
            region = Region.objects.get(
                election=self.election,
                region_number=int(self.eml.managing_authority.authority_identifier.id),
                region_name=managing_authority_name,
            )
            if self.file_path is not None:
                ElectionDocument.objects.create(
                    storage_key=self.file_path.relative_to(f"{settings.BASE_DIR}/.data").as_posix(),
                    region=region,
                    content_type="application/xml",
                    size=self.file_path.stat().st_size,
                    file_type=ElectionDocument.FILE_TYPE_EML510B,
                )

            region.results_available_at = timezone.now()
            counting_method = self._counting_method(self.eml.count)
            if counting_method is not None:
                region.counting_method = counting_method
            region.save()

        except Region.DoesNotExist:
            # Municipality does not exist in the election definition, so we shouldn't import it's results
            return

        # Preload party names dict
        party_by_list_number = {party.list_number: party for party in Party.objects.filter(election=self.election)}
        polling_stations = self._ensure_polling_stations(region)

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
                party_by_list_number,
                candidate_by_key,
                vote_counts,
            )
            self._collect_turnout_counts(contest, region, contest_data.total_votes, turnout_counts)
            for unit in contest_data.reporting_unit_votes:
                polling_station = polling_stations[
                    (str(unit.reporting_unit_identifier.id), self._polling_station_name(unit))
                ]
                self._parse_party_candidate_votecounts(
                    contest,
                    polling_station,
                    unit.selection,
                    party_by_list_number,
                    candidate_by_key,
                    vote_counts,
                )
                self._collect_turnout_counts(contest, polling_station, unit, turnout_counts)

        if vote_counts:
            VoteCount.objects.bulk_create(vote_counts, batch_size=BULK_BATCH_SIZE)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=BULK_BATCH_SIZE)


class EML510dImporter(EML510BaseImporter):
    """Totaaltelling."""

    eml_type = VoteCount.EML_TYPE_510D

    def _get_election_identifier_data(self):
        return self.eml.count.election.election_identifier

    def _parse_data(self) -> None:
        election_domain = self._get_election_identifier_data().election_domain
        if not isinstance(election_domain, list):
            election_domain = [election_domain]
        assert len(election_domain) == 1, "More than one election domain, cannot parse"
        region_number = int(election_domain[0].id) if election_domain[0].id else None
        region_name = election_domain[0].value
        # A Totaaltelling is published by a top-level body (gemeente, waterschap,
        # provincie, staat), never by a kieskring or a polling station. Those can
        # share both number and name with their parent -- waterschap Noorderzijlvest
        # has a kieskring called Noorderzijlvest with the same number -- which makes
        # an unfiltered lookup ambiguous (MultipleObjectsReturned).
        regions_qs = Region.objects.filter(election=self.election).exclude(
            region_category__in=(RegionCategory.KIESKRING, RegionCategory.STEMBUREAU)
        )
        if not region_number:
            # Allow for the case when the election domain has no region number attached,
            # this is the case in PS and region number is in that case not needed for retrieval
            region = regions_qs.get(region_name=region_name)
        else:
            region = regions_qs.get(
                region_number=region_number,
                region_name=region_name,
            )

        counting_method = self._counting_method(self.eml.count)
        if counting_method is not None and region.counting_method != counting_method:
            region.counting_method = counting_method
            region.save(update_fields=["counting_method", "updated_at"])

        # Preload party names dict
        party_by_list_number = {party.list_number: party for party in Party.objects.filter(election=self.election)}

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
                party_by_list_number,
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
                    party_by_list_number,
                    candidate_by_key,
                    vote_counts,
                )
                self._collect_turnout_counts(contest, gsb_region, unit, turnout_counts)

        if vote_counts:
            VoteCount.objects.bulk_create(vote_counts, batch_size=BULK_BATCH_SIZE)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=BULK_BATCH_SIZE)


class ElectionImporter:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._parser = build_parser()

    _DOCUMENT_TYPES: dict[str, tuple[type[Emlstructure], type[EMLBaseImporter]]] = {
        "110a": (Eml110a, EML110aImporter),  # Verkiezingsdefinitie
        "230b": (Eml230, EML230bImporter),  # Kandidatenlijst
        VoteCount.EML_TYPE_510B: (Eml510, EML510bImporter),  # Telling
        VoteCount.EML_TYPE_510D: (Eml510, EML510dImporter),  # Totaaltelling
    }

    @staticmethod
    def _root_element_id(source) -> str | None:
        # Only the root element is needed, so bail out on the first start event.
        for _, element in ET.iterparse(source, events=("start",)):
            return element.get("Id")
        return None

    @classmethod
    def _document_id(cls, xml_file_path: Path | BytesIO) -> str | None:
        if isinstance(xml_file_path, Path):
            # Open explicitly: returning early out of iterparse() otherwise leaves the
            # handle it opened for us to be closed by the GC, one per classified file.
            with xml_file_path.open("rb") as file_handle:
                return cls._root_element_id(file_handle)

        xml_file_path.seek(0)
        return cls._root_element_id(xml_file_path)

    def _process_file_paths(self, parser_type: str, xml_files: list[Path]) -> None:
        """
        Process the list of paths of `xml_files` using the parser for `parser_type`
        """
        binding, importer_cls = self._DOCUMENT_TYPES[parser_type]
        self.logger.info(f"Importing {parser_type} files using {importer_cls.__name__}...")
        file_cnt = len(xml_files)
        for i, xml_file_path in enumerate(xml_files, start=1):
            self.logger.info(f"Processing [{i}/{file_cnt}] {xml_file_path}...")
            eml = self._parser.from_path(xml_file_path, binding)
            # Use a transaction to prevent auto-commit round-trips for each insert query
            with transaction.atomic():
                importer_cls(eml, xml_file_path).parse()

    def _classify_files[T = Path | BytesIO](self, input_files: list[T]) -> dict[str, list[T]]:
        xml_files: dict[str, list[T]] = {key: [] for key in self._DOCUMENT_TYPES}
        for xml_file_path in input_files:
            document_id = self._document_id(xml_file_path)
            if document_id and document_id in xml_files:
                xml_files[document_id].append(xml_file_path)
        return xml_files

    def import_folder(self, folder: Path, workers: int = 1) -> None:
        """
        Import all XML files from the given folder.

        With `workers` > 1 the files of each document type are imported
        concurrently. The document types themselves stay sequential: 110a creates
        the regions and parties that 230b needs, and 230b creates the contests and
        candidates that 510b/510d need.
        """
        files = sorted(folder.rglob("*.xml"))
        xml_files = self._classify_files(files)

        workers = self._usable_workers(workers)
        if workers == 1:
            for parser_type in self._DOCUMENT_TYPES:
                self._process_file_paths(parser_type, xml_files[parser_type])
            return

        # django.setup is the initializer because it is picklable by reference and
        # importing `django` needs no app registry.
        # Hand no open connection to the children, and force "spawn" so a forked
        # child can never inherit this process's socket.
        connections.close_all()
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=django.setup,
        ) as pool:
            for parser_type in self._DOCUMENT_TYPES:
                # Each phase is a barrier: _process_file_paths_parallel does not
                # return until every file of this document type is imported.
                self._process_file_paths_parallel(pool, parser_type, xml_files[parser_type], workers)

    def _usable_workers(self, workers: int) -> int:
        """Refuse to spawn workers when they could not see the caller's data."""
        if workers > 1 and connection.in_atomic_block:
            # Worker processes get their own connections, so they cannot see rows
            # written inside the caller's still-open transaction (this is exactly
            # the case under pytest's django_db, which also renames the database).
            self.logger.warning(
                "Called inside an open transaction; importing serially instead of with %s workers.",
                workers,
            )
            return 1
        return workers

    def _process_file_paths_parallel(
        self,
        pool: ProcessPoolExecutor,
        parser_type: str,
        xml_files: list[Path],
        workers: int,
    ) -> None:
        """
        Import one document type on `pool`, one file per task.

        Files are dispatched individually rather than pre-chunked so the pool
        balances itself, and largest file first.
        """
        if not xml_files:
            return

        ordered = sorted(xml_files, key=lambda path: path.stat().st_size, reverse=True)

        _, importer_cls = self._DOCUMENT_TYPES[parser_type]
        self.logger.info(
            f"Importing {len(ordered)} {parser_type} files using {importer_cls.__name__} across {workers} workers..."
        )

        done = 0
        futures = [pool.submit(self._import_file, parser_type, str(path)) for path in ordered]
        for future in as_completed(futures):
            # Re-raise anything a worker raised, rather than losing it.
            processed_path = future.result()
            done += 1
            self.logger.info(f"[{done}/{len(ordered)}] Processed {parser_type} file {processed_path}...")

    @staticmethod
    def _import_file(parser_type: str, raw_path: str) -> str:
        """
        Parse and import a single EML file. Runs in a worker process.

        One task per file: the importers scope their writes to the region named by
        the file (its managing authority), so files of the same document type do
        not touch each other's rows even when they belong to one nationwide
        election.
        """
        global _WORKER_PARSER
        if _WORKER_PARSER is None:
            # Once per worker process, not once per file.
            _WORKER_PARSER = build_parser()

        binding, importer_cls = ElectionImporter._DOCUMENT_TYPES[parser_type]
        path = Path(raw_path)

        eml = _WORKER_PARSER.from_path(path, binding)
        with transaction.atomic():
            importer_cls(eml, path).parse()

        return raw_path

    def import_file_objects(self, files: list[NamedBytesIO]) -> None:
        """
        Import all given file-like objects.
        """
        xml_files = self._classify_files(files)
        for parser_type, (binding, importer_cls) in self._DOCUMENT_TYPES.items():
            for file in xml_files[parser_type]:
                self.logger.info(f"Importing {parser_type} file {file.filename}")
                eml = self._parser.from_bytes(file.getvalue(), binding)
                with transaction.atomic():
                    importer_cls(eml, None).parse()
