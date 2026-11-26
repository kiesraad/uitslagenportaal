from datetime import datetime

from rest_framework import serializers

from election.eml_dates import region_eml_dates
from election.models import ElectionDocument, TimelineVariant
from election.serializers import CertifiedDocumentSerializer, ElectionDocumentSerializer
from mainsite.models import RegionCategory
from mainsite.serializers import (
    RegionSummarySerializer,
    VoteCountSummarySerializer,
    VoterTurnoutCountSummarySerializer,
)
from mainsite.utils.eml_type import ReportingLevel
from region.models import Region, parse_station_number

CORRECTION_COUNT_FILE_TYPES = {
    RegionCategory.GEMEENTE: ElectionDocument.FileType.EML_510B,
    RegionCategory.KIESKRING: ElectionDocument.FileType.EML_510C,
}

# Which proces-verbaal the viewer shows, best first: corrections before the forms they correct, and a
# Bijlage 1 (counts per list and candidate) before its main form (totals per list only). Na 31-2 Bijlage 2
# holds no vote counts and is never shown.
VIEWER_PRIORITY = {
    file_type: rank
    for rank, file_type in enumerate(
        (
            ElectionDocument.FileType.PDF_P1F_1,
            ElectionDocument.FileType.PDF_NA14_2_B1,
            ElectionDocument.FileType.PDF_NA14_2,
            ElectionDocument.FileType.PDF_NA14_1,
            ElectionDocument.FileType.PDF_P22_1,
            ElectionDocument.FileType.PDF_P22_2,
            ElectionDocument.FileType.PDF_O7,
            ElectionDocument.FileType.PDF_NA31_2_B1,
            ElectionDocument.FileType.PDF_NA31_2,
            ElectionDocument.FileType.PDF_NA31_1,
            ElectionDocument.FileType.PDF_N10_1,
            ElectionDocument.FileType.PDF_N10_2,
        )
    )
}

FileType = ElectionDocument.FileType

# Per reporting level: whether the counts sit on the region's parent (a stembureau's come from the gemeente's
# 510b), and the count EML whose corrections can make it differ from the PV. The CSB's counts are never corrected.
COUNT_EML_BY_LEVEL = {
    ReportingLevel.SB: (True, FileType.EML_510B),
    ReportingLevel.GSB: (False, FileType.EML_510B),
    ReportingLevel.HSB: (False, FileType.EML_510C),
}


class SameLocationStationsField(serializers.Field):
    """The other stembureaus at the same location, from the view's `same_location_stations` annotation."""

    def __init__(self, **kwargs):
        super().__init__(source="*", read_only=True, **kwargs)

    def to_representation(self, region):
        stations = [
            {"station_number": parse_station_number(station["region_number"]), "slug": station["slug"]}
            for station in getattr(region, "same_location_stations", None) or []
        ]
        return sorted(stations, key=lambda station: station["station_number"] or 0)


class RegionListSerializer(serializers.ModelSerializer):
    csb = RegionSummarySerializer(read_only=True)
    station_number = serializers.IntegerField(read_only=True, allow_null=True)
    same_location_stations = SameLocationStationsField()
    has_results = serializers.BooleanField(read_only=True)

    class Meta:
        model = Region
        fields = (
            "region_name",
            "slug",
            "region_category",
            "csb",
            "station_number",
            "postal_code",
            "same_location_stations",
            "has_results",
        )


class RegionDetailSerializer(serializers.ModelSerializer):
    voter_turnout_counts = VoterTurnoutCountSummarySerializer(read_only=True, many=True)
    vote_counts = VoteCountSummarySerializer(read_only=True, many=True)
    documents = ElectionDocumentSerializer(read_only=True, many=True)
    certified_documents = serializers.SerializerMethodField()
    pv_may_differ = serializers.SerializerMethodField()
    timeline_variant = serializers.SerializerMethodField()
    correction_date = serializers.SerializerMethodField()
    eml_dates = serializers.SerializerMethodField()
    election_slug = serializers.CharField(source="election.slug", read_only=True)
    station_number = serializers.IntegerField(read_only=True, allow_null=True)
    same_location_stations = SameLocationStationsField()
    csb = RegionSummarySerializer(read_only=True)
    hsb = RegionSummarySerializer(read_only=True)

    class Meta:
        model = Region
        fields = (
            "voter_turnout_counts",
            "region_name",
            "vote_counts",
            "slug",
            "documents",
            "certified_documents",
            "pv_may_differ",
            "timeline_variant",
            "correction_date",
            "eml_dates",
            "region_category",
            "results_available_at",
            "election_slug",
            "station_number",
            "same_location_stations",
            "is_csb",
            "csb",
            "has_hsb",
            "hsb",
        )

    @staticmethod
    def _viewer_documents(region) -> list[ElectionDocument]:
        # The view prefetches only the documents of the requested level. The form type decides the order, not
        # the import date, which follows the scraping order. Among forms of the same type the newest comes first,
        # so the last of several stacked corrections leads.
        documents = [document for document in region.documents.all() if document.file_type in VIEWER_PRIORITY]
        return sorted(
            documents,
            key=lambda document: (
                VIEWER_PRIORITY[document.file_type],
                -document.created_at.timestamp(),
                -document.pk,
            ),
        )

    def get_certified_documents(self, region) -> list[dict]:
        """Every PV of the region the viewer can show, best first. Corrections are numbered across the region's
        corrections in import order; PV dates are not shown, as they follow the scraping order."""
        documents = self._viewer_documents(region)
        corrections = sorted(
            (document for document in documents if document.file_type in ElectionDocument.CORRECTION_FILE_TYPES),
            key=lambda document: (document.created_at, document.pk),
        )
        numbers = {document.pk: number for number, document in enumerate(corrections, start=1)}
        return [
            {**CertifiedDocumentSerializer(document).data, "correction_number": numbers.get(document.pk)}
            for document in documents
        ]

    def get_pv_may_differ(self, region) -> bool:
        """Whether the counts or a PV have been corrected, so the PV may not match the counts on the page yet.
        Neither side says reliably which correction goes with which, so only that one exists is told."""
        documents = self._viewer_documents(region)
        if not documents:
            return False
        if any(document.file_type in ElectionDocument.CORRECTION_FILE_TYPES for document in documents):
            return True
        request = self.context.get("request")
        level = request.query_params.get("level") if request else None
        if level not in COUNT_EML_BY_LEVEL:
            return False
        on_parent, eml_file_type = COUNT_EML_BY_LEVEL[level]
        region_id = region.parent_id if on_parent else region.pk
        # Identical files are skipped on import, so every count after the first is a corrigendum.
        return ElectionDocument.all_objects.filter(region_id=region_id, file_type=eml_file_type).count() > 1

    def get_eml_dates(self, region) -> dict:
        return region_eml_dates(region)

    def get_correction_date(self, region) -> datetime | None:
        """When the region's latest corrected count EML was created; None while it has only the original."""
        file_type = CORRECTION_COUNT_FILE_TYPES.get(region.region_category)
        if file_type is None:
            return None
        # Identical files are skipped on import, so every count after the first is a corrigendum.
        counts = ElectionDocument.all_objects.filter(region=region, file_type=file_type).order_by("-created_at", "-pk")
        if counts.count() < 2:
            return None
        latest = counts.first()
        # EMLs imported before eml_created_at existed fall back to their import time.
        return latest.eml_created_at or latest.created_at

    def get_timeline_variant(self, region) -> str:
        counting_method = region.counting_method or (region.parent.counting_method if region.parent else None)
        return counting_method or TimelineVariant.DEFAULT
