from abc import ABC

from django.conf import settings
from django.utils import timezone
from pyeml_bindings import (
    Count,
    CountingMethodMethodCode,
    Eml510,
    ReportingUnitVotes,
)

from election.models import (
    Contest,
    ElectionDocument,
    VoteCount,
    VoterTurnoutCount,
)
from eml_import.utils.eml_base_importer import EMLBaseImporter
from mainsite.exceptions import EMLImporterException
from mainsite.models import CountingMethod, RegionCategory
from party.models import Candidate, Party
from region.models import Region, build_region_slug


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
                except KeyError:
                    raise EMLImporterException(
                        (
                            "Candidate %s not found within party %s",
                            int(votes_item.candidate.candidate_identifier.id),
                            current_party.registered_name,
                        )
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
            VoteCount.objects.bulk_create(vote_counts, batch_size=self.BULK_BATCH_SIZE)
        if turnout_counts:
            VoterTurnoutCount.objects.bulk_create(turnout_counts, batch_size=self.BULK_BATCH_SIZE)
