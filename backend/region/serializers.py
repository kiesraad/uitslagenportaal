from rest_framework import serializers

from election.models import TimelineVariant
from election.serializers import ElectionDocumentSerializer, TimelineEntrySerializer
from mainsite.models import RegionCategory
from mainsite.serializers import (
    VoteCountSummarySerializer,
    VoterTurnoutCountSummarySerializer,
)
from mainsite.utils.eml_type import EmlType
from region.models import Region


class RegionListSerializer(serializers.ModelSerializer):
    csb_name = serializers.CharField(source="csb.region_name", default=None, read_only=True)
    csb_slug = serializers.SlugField(source="csb.slug", default=None, read_only=True)
    station_number = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ("region_name", "slug", "region_category", "csb_name", "csb_slug", "station_number")

    def get_station_number(self, region) -> int | None:
        if region.region_category != RegionCategory.STEMBUREAU:
            return None
        station = str(region.region_number).split("::")[-1].removeprefix("SB")
        return int(station) if station.isdigit() else None


class RegionDetailSerializer(serializers.ModelSerializer):
    voter_turnout_counts = serializers.SerializerMethodField()
    vote_counts = serializers.SerializerMethodField()
    timeline_entries = serializers.SerializerMethodField()
    timeline_variant = serializers.SerializerMethodField()
    documents = ElectionDocumentSerializer(many=True, read_only=True)
    csb_name = serializers.CharField(source="csb.region_name", default=None, read_only=True)
    csb_slug = serializers.SlugField(source="csb.slug", default=None, read_only=True)
    election_slug = serializers.CharField(source="election.slug", read_only=True)

    def get_vote_counts(self, obj):
        vote_counts = list(obj.vote_counts.filter(is_current=True))
        if obj.region_category == RegionCategory.GEMEENTE:
            vote_counts = [vc for vc in vote_counts if vc.eml_type == EmlType.EML_510b]
        return VoteCountSummarySerializer(vote_counts, many=True).data

    def get_voter_turnout_counts(self, obj):
        turnout_counts = list(obj.voter_turnout_counts.filter(is_current=True))
        if obj.region_category == RegionCategory.GEMEENTE:
            turnout_counts = [tc for tc in turnout_counts if tc.eml_type == EmlType.EML_510b]
        return VoterTurnoutCountSummarySerializer(turnout_counts, many=True).data

    class Meta:
        model = Region
        fields = (
            "voter_turnout_counts",
            "region_name",
            "vote_counts",
            "slug",
            "documents",
            "timeline_entries",
            "timeline_variant",
            "region_category",
            "results_available_at",
            "csb_name",
            "csb_slug",
            "election_slug",
        )

    def _effective_variant(self, region) -> str:
        counting_method = region.counting_method or (region.parent.counting_method if region.parent else None)
        return counting_method or TimelineVariant.DEFAULT

    def get_timeline_variant(self, region) -> str:
        return self._effective_variant(region)

    def get_timeline_entries(self, region):
        variant = self._effective_variant(region)
        entries = [
            entry for entry in region.election.election_config.timeline_entries.all() if entry.variant == variant
        ]
        return TimelineEntrySerializer(entries, many=True).data
