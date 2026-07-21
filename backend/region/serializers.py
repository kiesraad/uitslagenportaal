from rest_framework import serializers

from election.models import TimelineVariant
from election.serializers import TimelineEntrySerializer, ElectionDocumentSerializer
from region.models import Region
from mainsite.models import RegionCategory
from mainsite.serializers import (
    VoteCountSummarySerializer,
    VoterTurnoutCountSummarySerializer,
)
from region.models import Region


class RegionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("region_name", "slug")


class RegionDetailSerializer(serializers.ModelSerializer):
    voter_turnout_counts = VoterTurnoutCountSummarySerializer(many=True, read_only=True)
    vote_counts = VoteCountSummarySerializer(many=True, read_only=True)
    timeline_entries = serializers.SerializerMethodField()
    documents = ElectionDocumentSerializer(many=True, read_only=True)

    def get_vote_counts(self, obj):
        """
        GSB counts are present in 510d and 510b, which duplicates them in the backend.
        We need both, but on GSB level the UI only needs the GSB (510b) results. That's why
        we filter it here to avoid duplication in the response data.
        """
        vote_counts = obj.vote_counts.filter(region=obj)
        if obj.region_category == RegionCategory.GEMEENTE:
            vote_counts = vote_counts.filter(eml_type="510b")
        serializer = VoteCountSummarySerializer(vote_counts, many=True, read_only=True)
        return serializer.data

    class Meta:
        model = Region
        fields = (
            "voter_turnout_counts",
            "region_name",
            "vote_counts",
            "slug",
            "documents",
            "timeline_entries",
        )

    def _effective_variant(self, region) -> str:
        counting_method = region.counting_method or (region.parent.counting_method if region.parent else None)
        return counting_method or TimelineVariant.DEFAULT

    def get_timeline_entries(self, region):
        variant = self._effective_variant(region)
        entries = [
            entry for entry in region.election.election_config.timeline_entries.all() if entry.variant == variant
        ]
        return TimelineEntrySerializer(entries, many=True).data
