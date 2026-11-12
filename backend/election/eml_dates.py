"""When each timeline step was completed, according to the EMLs of the regions it covers."""

from datetime import date, datetime

from django.db.models import Min, Q, QuerySet

from election.models import ElectionConfig, ElectionDocument, TimelineEvent
from mainsite.models import RegionCategory
from region.models import Region, hsb_kieskringen

FileType = ElectionDocument.FileType


def _completed_at(regions: QuerySet[Region], file_type: str) -> datetime | None:
    """When the last of the regions created its first EML of file_type; None while any region has none."""
    total = regions.count()
    if total == 0:
        return None
    # A corrigendum does not move the step: each region counts with its first (original) EML.
    firsts = list(
        ElectionDocument.all_objects.filter(region__in=regions, file_type=file_type)
        .values("region")
        .annotate(first=Min("eml_created_at"))
        .values_list("first", flat=True)
    )
    if len(firsts) < total or None in firsts:
        return None
    return max(firsts)


def _dates(
    election_date: date | None,
    gemeenten: QuerySet[Region],
    kieskringen: QuerySet[Region],
    csbs: QuerySet[Region],
) -> dict[str, date | datetime | None]:
    has_count = ElectionDocument.all_objects.filter(region__in=gemeenten, file_type=FileType.EML_510B).exists()
    return {
        # Stembureaus count on the evening of election day, so that day is known once any count is in.
        TimelineEvent.SB_VOTE_COUNT: election_date if has_count else None,
        TimelineEvent.MUNICIPALITY_VOTE_COUNT: _completed_at(gemeenten, FileType.EML_510B),
        TimelineEvent.ELECTORAL_DISTRICT_VOTE_COUNT: _completed_at(kieskringen, FileType.EML_510C),
        TimelineEvent.CSB_RESULT_PUBLISH: _completed_at(csbs, FileType.EML_520),
    }


def region_eml_dates(region: Region) -> dict[str, date | datetime | None]:
    """The steps of a region's page: its own gemeente(n), and the kieskring and CSB above or below it."""
    regions = Region.objects.filter(election=region.election)
    match region.region_category:
        case RegionCategory.STEMBUREAU:
            gemeenten = regions.filter(pk=region.parent_id)
        case RegionCategory.GEMEENTE:
            gemeenten = regions.filter(pk=region.pk)
        case _:
            gemeenten = regions.filter(
                Q(parent=region) | Q(csb=region), region_category=RegionCategory.GEMEENTE
            ).distinct()

    if region.region_category == RegionCategory.KIESKRING:
        kieskringen = regions.filter(pk=region.pk)
    elif region.is_csb:
        kieskringen = hsb_kieskringen(regions.filter(parent=region))
    else:
        hsb = region.hsb
        kieskringen = hsb_kieskringen(regions).filter(pk=hsb.pk if hsb else None)

    csbs = regions.filter(pk=region.pk if region.is_csb else region.csb_id)
    return _dates(region.election.date, gemeenten, kieskringen, csbs)


def election_config_eml_dates(election_config: ElectionConfig) -> dict[str, date | datetime | None]:
    """The steps of the general timeline, over every region of the election."""
    regions = Region.objects.filter(election__election_config=election_config)
    election = election_config.elections.first()
    return _dates(
        election.date if election else None,
        regions.filter(region_category=RegionCategory.GEMEENTE),
        hsb_kieskringen(regions),
        regions.filter(region_category=election_config.csb_type),
    )
