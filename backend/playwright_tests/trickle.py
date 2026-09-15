"""Build Waterschap portal states with the ORM, one pause at a time."""

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from election.models import (
    Contest,
    Election,
    ElectionCategory,
    ElectionConfig,
    ElectionDocument,
    TimelineVariant,
    VoteCount,
)
from election.tests.factories import (
    ContestFactory,
    ElectionConfigFactory,
    ElectionDocumentFactory,
    ElectionFactory,
    TimelineEntryFactory,
)
from election.utils import visibility_cutoff
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EmlType
from party.models import Candidate, Party
from party.tests.factories import CandidateFactory, PartyFactory
from region.models import Region
from region.tests.factories import RegionFactory

WS_LABEL = "Waterschapsverkiezingen 2023"
PS_LABEL = "Provinciale Statenverkiezingen 2023"
GR_LABEL = "Gemeenteraadsverkiezingen 2026"
TK_LABEL = "Tweede Kamer Verkiezingen 2025"


def visible_config(blocker, *, identifier: str, label: str, category: str) -> ElectionConfig:
    with blocker.unblock():
        return ElectionConfigFactory(
            identifier=identifier,
            label=label,
            category=category,
            date=timezone.now() - timedelta(days=1),
        )


def expired_config(blocker, *, identifier: str, label: str, category: str) -> ElectionConfig:
    with blocker.unblock():
        return ElectionConfigFactory(
            identifier=identifier,
            label=label,
            category=category,
            date=visibility_cutoff() - timedelta(days=1),
        )


def add_home_timeline(blocker, config: ElectionConfig) -> None:
    with blocker.unblock():
        TimelineEntryFactory(
            election_config=config,
            variant=TimelineVariant.DEFAULT,
            title_nl="Telling in de stembureaus",
            title_en="Count at the polling stations",
        )


def _party_count(contest: Contest, region: Region, party: Party, votes: int, eml_type: EmlType) -> None:
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        valid_votes=votes,
        result_level=VoteCount.RESULT_LEVEL_PARTY,
        eml_type=eml_type,
    )


def _candidate_count(
    contest: Contest,
    region: Region,
    party: Party,
    candidate: Candidate,
    votes: int,
    eml_type: EmlType,
) -> None:
    VoteCount.objects.create(
        contest=contest,
        region=region,
        party=party,
        candidate=candidate,
        valid_votes=votes,
        result_level=VoteCount.RESULT_LEVEL_CANDIDATE,
        eml_type=eml_type,
    )


@dataclass
class WsPortal:
    config: ElectionConfig
    election: Election
    waterschap: Region
    borsele: Region
    goes: Region
    zeeland: Party
    cda: Party
    contest: Contest | None = None
    minderhoud: Candidate | None = None


def ws_definition(blocker) -> WsPortal:
    """Election, region tree and registered parties — as after a 110a."""
    with blocker.unblock():
        config = ElectionConfigFactory(
            identifier="AB2023",
            label=WS_LABEL,
            category=ElectionCategory.WS.value,
            date=timezone.now() - timedelta(days=1),
        )
        TimelineEntryFactory(
            election_config=config,
            variant=TimelineVariant.DEFAULT,
            title_nl="Telling in de stembureaus",
            title_en="Count at the polling stations",
        )
        election = ElectionFactory(election_config=config, name="Scheldestromen", subcategory="AB2")
        waterschap = RegionFactory(
            election=election,
            region_category=RegionCategory.WATERSCHAP,
            region_number="17",
            region_name="Scheldestromen",
        )
        # 110a numbers this kieskring 1, not 17 like the waterschap.
        kieskring = RegionFactory(
            election=election,
            parent=waterschap,
            csb=waterschap,
            region_category=RegionCategory.KIESKRING,
            region_number="1",
            region_name="Scheldestromen",
        )
        borsele = RegionFactory(
            election=election,
            parent=kieskring,
            csb=waterschap,
            region_category=RegionCategory.GEMEENTE,
            region_number="654",
            region_name="Borsele",
        )
        goes = RegionFactory(
            election=election,
            parent=kieskring,
            csb=waterschap,
            region_category=RegionCategory.GEMEENTE,
            region_number="664",
            region_name="Goes",
        )
        zeeland = PartyFactory(election=election, registered_name="Partij voor Zeeland")
        cda = PartyFactory(election=election, registered_name="CDA")
    return WsPortal(
        config=config,
        election=election,
        waterschap=waterschap,
        borsele=borsele,
        goes=goes,
        zeeland=zeeland,
        cda=cda,
    )


def add_candidate_lists(blocker, ws: WsPortal) -> None:
    with blocker.unblock():
        ws.contest = ContestFactory(election=ws.election, identifier="geen")
        ws.zeeland.list_number = 1
        ws.zeeland.save(update_fields=["list_number", "updated_at"])
        ws.cda.list_number = 2
        ws.cda.save(update_fields=["list_number", "updated_at"])
        ws.minderhoud = CandidateFactory(
            contest=ws.contest,
            party=ws.zeeland,
            identifier=1,
            position=1,
            last_name="Minderhoud",
        )
        CandidateFactory(
            contest=ws.contest,
            party=ws.cda,
            identifier=1,
            position=1,
            last_name="Jansen",
        )


def add_borsele_telling(blocker, ws: WsPortal) -> None:
    assert ws.contest is not None and ws.minderhoud is not None
    with blocker.unblock():
        station = RegionFactory(
            election=ws.election,
            parent=ws.borsele,
            csb=ws.waterschap,
            region_category=RegionCategory.STEMBUREAU,
            region_number="0654::SB1",
            region_name="Heinkenszand",
        )
        ws.borsele.results_available_at = timezone.now()
        ws.borsele.save(update_fields=["results_available_at", "updated_at"])
        ElectionDocumentFactory(
            region=ws.borsele,
            file_type=ElectionDocument.FileType.EML_510B,
            size=1024,
        )
        for region in (ws.borsele, station):
            _party_count(ws.contest, region, ws.zeeland, 100, EmlType.EML_510b)
            _party_count(ws.contest, region, ws.cda, 50, EmlType.EML_510b)
            _candidate_count(ws.contest, region, ws.zeeland, ws.minderhoud, 80, EmlType.EML_510b)


def add_csb_totaaltelling(blocker, ws: WsPortal) -> None:
    assert ws.contest is not None and ws.minderhoud is not None
    with blocker.unblock():
        ws.waterschap.results_available_at = timezone.now()
        ws.waterschap.save(update_fields=["results_available_at", "updated_at"])
        ElectionDocumentFactory(
            region=ws.waterschap,
            file_type=ElectionDocument.FileType.EML_510D,
            size=2048,
        )
        _party_count(ws.contest, ws.waterschap, ws.zeeland, 142, EmlType.EML_510d)
        _party_count(ws.contest, ws.waterschap, ws.cda, 70, EmlType.EML_510d)
        _candidate_count(ws.contest, ws.waterschap, ws.zeeland, ws.minderhoud, 90, EmlType.EML_510d)
        _party_count(ws.contest, ws.borsele, ws.zeeland, 99, EmlType.EML_510d)
        _candidate_count(ws.contest, ws.borsele, ws.zeeland, ws.minderhoud, 70, EmlType.EML_510d)
        # Goes has CSB numbers only: the matrix shows them, the GSB page must not.
        _party_count(ws.contest, ws.goes, ws.zeeland, 43, EmlType.EML_510d)
        _candidate_count(ws.contest, ws.goes, ws.zeeland, ws.minderhoud, 20, EmlType.EML_510d)
