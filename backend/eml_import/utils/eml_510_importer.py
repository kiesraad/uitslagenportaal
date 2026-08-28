import re
from abc import ABC
from datetime import datetime
from io import BytesIO
from pathlib import Path

from django.core.files.storage import default_storage
from django.utils import timezone
from pyeml_bindings import (
    Count,
    CountingMethodMethodCode,
    Eml510,
    ReportingUnitVotes,
)

from election.models import (
    Contest,
    ElectionCategory,
    ElectionDocument,
    VoteCount,
    VoterTurnoutCount,
)
from eml_import.exceptions import EMLImporterException
from eml_import.utils.eml_base_importer import EMLBaseImporter
from eml_import.utils.named_bytes_io import NamedBytesIO
from mainsite.models import CountingMethod, RegionCategory
from mainsite.utils.eml_type import EmlType
from party.models import Candidate, Party
from region.models import Region, build_region_slug


class EML510BaseImporter(EMLBaseImporter[Eml510], ABC):
    def __init__(self, eml: Eml510, eml_file: Path | NamedBytesIO | None):
        super().__init__(eml, eml_file)
        self.election_documents = {doc.storage_key: doc for doc in ElectionDocument.objects.all()}

    def _results_available_at(self) -> datetime | None:
        """
        Publication time of the results, from the EML's <kr:CreationDateTime>.
        Optional and repeatable in the schema, and the Kiesraad writes it
        without a UTC offset, so it is read as a naive datetime in the local timezone.
        """
        creation_date_time = self.eml.creation_date_time
        if not creation_date_time:
            return None
        value = creation_date_time[0].value
        if value is None:
            return None
        created = value.to_datetime()
        if timezone.is_naive(created):
            created = timezone.make_aware(created)
        return created

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
        contest: Contest,
        region: Region,
        items: list[Count.Election.Contests.Contest.TotalVotes.Selection | ReportingUnitVotes.Selection],
        party_by_list_nuber: dict[int, Party],
        candidate_by_key: dict[tuple[int | None, int], Candidate],
        vote_counts: list[VoteCount],
        *,
        candidate_by_short_code: dict[tuple[int, str], int] | None = None,
    ) -> None:
        current_party: Party | None = None
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
                candidate_id = votes_item.candidate.candidate_identifier.id
                candidate_short_code = votes_item.candidate.candidate_identifier.short_code_attribute
                try:
                    assert candidate_id is not None or candidate_short_code is not None
                    if candidate_id is not None:
                        candidate = candidate_by_key[(current_party.id, int(candidate_id))]

                        if candidate_by_short_code is not None:
                            # Store candidate-short code mapping for later use. We have to save the candidate's DB id
                            # because when processing total votecounts for candidates that belong to a HSB-specific
                            # contest, we can't fetch them by position/identifier.
                            if candidate_id is not None and candidate_short_code is not None:
                                candidate_by_short_code[(current_party.id, candidate_short_code)] = candidate.id
                    else:
                        # Candidate identifier is None, meaning we have to fetch them by short code from the mapping
                        # created when processing reporting units' votes.
                        candidate_id = candidate_by_short_code.get((current_party.id, candidate_short_code))
                        candidate = candidate_by_key[(None, candidate_id)]
                except KeyError:
                    candidate_identifier = candidate_id or candidate_short_code
                    raise EMLImporterException(
                        f"Candidate {candidate_identifier} not found within party {current_party.registered_name}"
                    )
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
                reason_code="total counted",
                votes=votes.total_counted,
                eml_type=self.eml_type,
            )
        )

    def _store_eml(self, region: Region) -> None:
        # Determine the name, it should be consistent based on the file content/type, so we store only one file
        # if the same file gets imported twice with a different filename.
        parent_number, parent_name = (
            (region.parent.region_number, region.parent.region_name) if region.parent else (None, None)
        )
        filename = "_".join(
            filter(
                lambda x: x,
                [
                    self.election_config.identifier,
                    self.eml_type.label,
                    parent_number,
                    parent_name,
                    region.region_number,
                    region.region_name,
                ],
            )
        )
        filename = re.sub(r"[^A-Za-z0-9_-]", "", filename.replace(" ", "_"))
        file_path = f"{self.election_config.identifier}/{filename}.eml.xml"

        # Store the file into the default storage
        if isinstance(self.eml_file, Path):
            file_content = BytesIO(self.eml_file.read_bytes())
        else:
            file_content = self.eml_file
        file_content.seek(0)
        size = len(file_content.getvalue())
        stored_file_path = default_storage.save(file_path, file_content)

        # We only call this once for the whole EML file, so a get_or_create doesn't result in an N+1 query.
        # size is only a default (not a lookup key): storage_key is unique, so if a re-imported file's
        # size differs from what's stored, looking it up by size too would miss the existing row and
        # attempt to insert a duplicate storage_key.
        doc, created = ElectionDocument.objects.get_or_create(
            storage_key=stored_file_path,
            region=region,
            content_type="application/xml",
            file_type=ElectionDocument.FileType.EML510B,
            defaults={"size": size},
        )
        # Update size on re-import
        if not created and doc.size != size:
            doc.size = size
            doc.save()


class EML510bImporter(EML510BaseImporter):
    """Telling"""

    eml_type = EmlType.EML_510b

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

        csb = self._csb_for_parent(region)
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
            batch_size=self.BULK_BATCH_SIZE,
        )

        return {
            (station.region_number, station.region_name): station
            for station in Region.objects.filter(**stations_filter)
        }

    def _parse_data(self) -> None:
        authority_el = self.eml.managing_authority.authority_identifier
        managing_authority_name = (authority_el.value or "").strip()
        authority_id = int(self.eml.managing_authority.authority_identifier.id)

        try:
            region = Region.objects.get(
                election=self.election,
                region_number=authority_id,
                region_name=managing_authority_name,
            )
        except Region.DoesNotExist:
            raise EMLImporterException(
                f"Municipality {managing_authority_name} {authority_id} "
                f"does not exist in the election definition of election {self.election.name}"
            )

        if self.eml_file is not None:
            self._store_eml(region)

        region.results_available_at = self._results_available_at()
        counting_method = self._counting_method(self.eml.count)
        if counting_method is not None:
            region.counting_method = counting_method
        region.save()

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
            VoteCount.objects.bulk_create(vote_counts, batch_size=self.BULK_BATCH_SIZE)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=self.BULK_BATCH_SIZE)


class EML510dImporter(EML510BaseImporter):
    """Totaaltelling."""

    eml_type = EmlType.EML_510d

    def _get_election_identifier_data(self):
        return self.eml.count.election.election_identifier

    def _parse_data(self) -> None:
        election_domain = self._get_election_identifier_data().election_domain
        if not isinstance(election_domain, list):
            election_domain = [election_domain]
        assert len(election_domain) == 1, "More than one election domain, cannot parse"
        region_number = int(election_domain[0].id) if election_domain[0].id else None
        region_name = election_domain[0].value

        # We're processing CSB results, but the region_category for CSBs differs per election category,
        # so get it from the category config.
        election_category = ElectionCategory(self.election.election_config.category)
        regions_qs = Region.objects.filter(election=self.election, region_category=election_category.config.csb)
        if not region_number:
            # Allow for the case when the election domain has no region number attached,
            # this is the case in PS and region number is in that case not needed for retrieval
            region = regions_qs.get(region_name=region_name)
        else:
            region = regions_qs.get(
                region_number=region_number,
                region_name=region_name,
            )

        update_fields = ["results_available_at", "updated_at"]
        region.results_available_at = self._results_available_at()
        counting_method = self._counting_method(self.eml.count)
        if counting_method is not None and region.counting_method != counting_method:
            region.counting_method = counting_method
            update_fields.append("counting_method")
        region.save(update_fields=update_fields)

        # Store the EML file
        if self.eml_file is not None:
            self._store_eml(region)

        # Preload party names dict and child regions by name
        party_by_list_number = {party.list_number: party for party in Party.objects.filter(election=self.election)}
        child_region_category = RegionCategory.GEMEENTE if region.children.count() == 1 else RegionCategory.KIESKRING
        child_region_by_name = {
            region.region_name: region
            for region in Region.objects.filter(election=self.election, region_category=child_region_category)
        }
        child_region_category_re = re.compile(child_region_category.label, re.IGNORECASE)

        vote_counts: list[VoteCount] = []
        turnout_counts: list[VoterTurnoutCount] = []
        for contest_data in self.eml.count.election.contests.contest:
            # Populated by self._parse_party_candidate_votecounts() when processing reporting unit's votes
            candidate_by_short_code = {}

            # Breakdown per child region (HSB/GSB)
            for unit in contest_data.reporting_unit_votes:
                # Get child region name without region category prefix (e.g. kieskring)
                child_region_name = child_region_category_re.sub("", unit.reporting_unit_identifier.value).strip()
                child_region = child_region_by_name.get(child_region_name)
                if child_region is None:
                    continue

                contest_filter = {"election": self.election}
                # Get the contest from the DB by name, if the contest in the EML file is set to 'alle'. This means that
                # the candidates are linked to a contest per reporting unit, so we get the contest by name.
                if contest_data.contest_identifier.id == "alle":
                    contest_filter["name"] = child_region_name
                else:
                    contest_filter["identifier"] = contest_data.contest_identifier.id
                contest = Contest.objects.get(**contest_filter)
                candidate_by_key = {
                    (candidate.party_id, candidate.identifier): candidate
                    for candidate in Candidate.objects.filter(contest=contest)
                }

                self._parse_party_candidate_votecounts(
                    contest,
                    child_region,
                    unit.selection,
                    party_by_list_number,
                    candidate_by_key,
                    vote_counts,
                    candidate_by_short_code=candidate_by_short_code,
                )
                self._collect_turnout_counts(contest, child_region, unit, turnout_counts)

            # CSB totals
            contest = Contest.objects.get(
                identifier=contest_data.contest_identifier.id,
                election=self.election,
            )
            # Get candidates by (party, identifier) and by (None, DB id) key.
            # We need to get candidates by DB id when processing contest-spanning totals. The DB ids are determined by
            # the short code mapping, which is tracked when processing the reporting unit's votes.
            candidate_by_key = {
                (candidate.party_id, candidate.identifier): candidate
                for candidate in Candidate.objects.filter(contest=contest)
            } | {
                (None, candidate.id): candidate
                for candidate in Candidate.objects.filter(contest__election=self.election)
            }
            self._parse_party_candidate_votecounts(
                contest,
                region,
                contest_data.total_votes.selection,
                party_by_list_number,
                candidate_by_key,
                vote_counts,
                candidate_by_short_code=candidate_by_short_code,
            )
            self._collect_turnout_counts(contest, region, contest_data.total_votes, turnout_counts)

        if vote_counts:
            VoteCount.objects.bulk_create(vote_counts, batch_size=self.BULK_BATCH_SIZE)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=self.BULK_BATCH_SIZE)
