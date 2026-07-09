from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from .models import (
    Election,
    Region,
    PollingStation,
    Contest,
    Affiliation,
    Candidate,
    Telling,
    ResultUnit,
    AffiliationVote,
    CandidateVote,
    UnitSummary,
)


def get_election(election_id):
    return get_object_or_404(Election, election_id=election_id, deleted_on__isnull=True)


def get_region(election, region_number, category=None):
    qs = election.regions.filter(region_number=region_number, deleted_on__isnull=True)
    if category:
        qs = qs.filter(category=category)
    return get_object_or_404(qs)


def gemeenten_for(election, parent_region=None):
    qs = election.regions.filter(category="GEMEENTE", deleted_on__isnull=True)
    if parent_region is not None:
        qs = qs.filter(parent=parent_region)
    return qs.order_by("name")


def current_telling_for_region(region):
    return (
        Telling.objects.filter(region=region, deleted_on__isnull=True)
        .order_by("-is_current", "-uploaded_at")
        .first()
    )


def total_unit_for_region(region):
    telling = current_telling_for_region(region)
    if telling is None:
        return None
    return (
        telling.units.filter(unit_type=ResultUnit.TOTAL, deleted_on__isnull=True)
        .select_related("summary")
        .prefetch_related(
            Prefetch(
                "affiliation_results",
                queryset=AffiliationVote.objects.filter(deleted_on__isnull=True)
                .select_related("affiliation")
                .order_by("affiliation__affiliation_id"),
            )
        )
        .first()
    )


def polling_station_unit(election, sb_code):
    station = get_object_or_404(
        PollingStation,
        sb_code=sb_code,
        municipality__election=election,
        deleted_on__isnull=True,
    )
    unit = (
        ResultUnit.objects.filter(polling_station=station, deleted_on__isnull=True)
        .select_related("summary", "submission")
        .prefetch_related(
            Prefetch(
                "affiliation_results",
                queryset=AffiliationVote.objects.filter(deleted_on__isnull=True)
                .select_related("affiliation")
                .order_by("affiliation__affiliation_id"),
            )
        )
        .first()
    )
    return station, unit


def candidate_votes_for(result_unit, affiliation_id):
    if result_unit is None:
        return Affiliation.objects.none(), CandidateVote.objects.none()

    affiliation = get_object_or_404(
        Affiliation,
        affiliation_id=affiliation_id,
        contest__election=result_unit.submission.election,
        deleted_on__isnull=True,
    )
    votes = (
        CandidateVote.objects.filter(
            result_unit=result_unit,
            candidate__affiliation=affiliation,
            deleted_on__isnull=True,
        )
        .select_related("candidate")
        .order_by("candidate__candidate_id")
    )
    return affiliation, votes
