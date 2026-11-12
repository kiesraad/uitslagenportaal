from datetime import datetime

from django.core.files.storage import default_storage
from django.urls import reverse
from rest_framework import serializers

from election.models import ElectionDocument, TimelineVariant
from election.serializers import ElectionDocumentSerializer
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
    certified_document_url = serializers.SerializerMethodField()
    certified_document_preview_url = serializers.SerializerMethodField()
    timeline_variant = serializers.SerializerMethodField()
    correction_date = serializers.SerializerMethodField()
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
            "certified_document_url",
            "certified_document_preview_url",
            "timeline_variant",
            "correction_date",
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

    def _certified_document(self, region):
        # The view prefetches only the documents of the requested level.
        documents = sorted(
            (
                document
                for document in region.documents.all()
                if document.file_type in ElectionDocument.CERTIFIED_FILE_TYPES
            ),
            key=lambda document: (document.created_at, document.pk),
            reverse=True,
        )
        corrections = (
            document for document in documents if document.file_type in ElectionDocument.CORRECTION_FILE_TYPES
        )
        return next(corrections, None) or next(iter(documents), None)

    def get_certified_document_url(self, region) -> str | None:
        document = self._certified_document(region)
        if document is None or not default_storage.exists(document.storage_key):
            return None
        return reverse("certified-document", kwargs={"pk": document.pk})

    def get_certified_document_preview_url(self, region) -> str | None:
        document = self._certified_document(region)
        if document is None:
            return None
        preview_key = document.preview_storage_key
        if not default_storage.exists(preview_key):
            return None
        return reverse("certified-document-preview", kwargs={"pk": document.pk})

    def get_correction_date(self, region) -> datetime | None:
        """When the region's latest corrected count EML came in; None while it has only the original."""
        file_type = CORRECTION_COUNT_FILE_TYPES.get(region.region_category)
        if file_type is None:
            return None
        # Identical files are skipped on import, so every count after the first is a corrigendum.
        counts = ElectionDocument.all_objects.filter(region=region, file_type=file_type).order_by("-created_at", "-pk")
        if counts.count() < 2:
            return None
        return counts.first().created_at

    def get_timeline_variant(self, region) -> str:
        counting_method = region.counting_method or (region.parent.counting_method if region.parent else None)
        return counting_method or TimelineVariant.DEFAULT
