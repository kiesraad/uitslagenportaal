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

# Per proces-verbaal in the viewer: whether its counts sit on the region's parent (a stembureau's come from the
# gemeente's 510b), the count EML, and the corrigenda that go with a corrected EML.
_STEMBUREAU = (True, FileType.EML_510B, {FileType.PDF_NA14_1, FileType.PDF_NA14_2_B1})
_GEMEENTE = (False, FileType.EML_510B, {FileType.PDF_NA14_2})
_HSB = (False, FileType.EML_510C, {FileType.PDF_P1F_1})
PV_CORRECTIONS = {
    FileType.PDF_N10_1: _STEMBUREAU,
    FileType.PDF_N10_2: _STEMBUREAU,
    FileType.PDF_NA31_2_B1: _STEMBUREAU,
    FileType.PDF_NA14_1: _STEMBUREAU,
    FileType.PDF_NA14_2_B1: _STEMBUREAU,
    FileType.PDF_NA31_1: _GEMEENTE,
    FileType.PDF_NA31_2: _GEMEENTE,
    FileType.PDF_NA14_2: _GEMEENTE,
    FileType.PDF_O7: _HSB,
    FileType.PDF_P1F_1: _HSB,
}


def pv_matches_counts(region: Region, document: ElectionDocument) -> bool:
    """Whether the PV has been corrected as often as the count EML, so both show the same numbers."""
    if document.file_type not in PV_CORRECTIONS:
        return True
    on_parent, eml_file_type, correction_file_types = PV_CORRECTIONS[document.file_type]
    region_id = region.parent_id if on_parent else region.pk
    # Identical files are skipped on import, so every count after the first is a corrigendum.
    eml_versions = ElectionDocument.all_objects.filter(region_id=region_id, file_type=eml_file_type).count()
    if not eml_versions:
        return True
    eml_corrections = eml_versions - 1
    pv_corrections = sum(1 for other in region.documents.all() if other.file_type in correction_file_types)
    if on_parent:
        # A corrected 510b need not change every stembureau, so only whether both sides are corrected is compared.
        return (eml_corrections > 0) == (pv_corrections > 0)
    return eml_corrections == pv_corrections


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
    certified_document = serializers.SerializerMethodField()
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
            "certified_document",
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

    def to_representation(self, region):
        data = super().to_representation(region)
        # A PV whose corrections differ from those of the counts is withheld, as its numbers differ from the page's.
        document = self._viewer_document(region)
        data["certified_document_mismatch"] = bool(document) and not pv_matches_counts(region, document)
        if data["certified_document_mismatch"]:
            data["certified_document"] = None
        return data

    @staticmethod
    def _viewer_document(region) -> ElectionDocument | None:
        # The view prefetches only the documents of the requested level. The form type decides which one is
        # shown, not the import date, which follows the scraping order. Among forms of the same type the
        # newest one wins, so the last of several stacked corrections is shown.
        documents = [document for document in region.documents.all() if document.file_type in VIEWER_PRIORITY]
        return min(
            documents,
            key=lambda document: (
                VIEWER_PRIORITY[document.file_type],
                -document.created_at.timestamp(),
                -document.pk,
            ),
            default=None,
        )

    def get_certified_document(self, region) -> dict | None:
        document = self._viewer_document(region)
        return CertifiedDocumentSerializer(document).data if document else None

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
