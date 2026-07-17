from rest_framework import serializers

from election.models import TimelineVariant
from election.serializers import TimelineEntrySerializer
from region.models import Region
from mainsite.serializers import (
    VoteCountSummarySerializer,
    VoterTurnoutCountSummarySerializer,
)


class RegionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("region_name", "slug")


class RegionDetailSerializer(serializers.ModelSerializer):

    voter_turnout_counts = VoterTurnoutCountSummarySerializer(many=True, read_only=True)
    vote_counts = VoteCountSummarySerializer(many=True, read_only=True)
    timeline_entries = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = (
            "voter_turnout_counts",
            "region_name",
            "vote_counts",
            "slug",
            "timeline_entries",
        )

    def _effective_variant(self, region) -> str:
        counting_method = region.counting_method or (
            region.parent.counting_method if region.parent else None
        )
        return counting_method or TimelineVariant.DEFAULT

    def get_timeline_entries(self, region):
        variant = self._effective_variant(region)
        entries = [
            entry
            for entry in region.election.election_config.timeline_entries.all()
            if entry.variant == variant
        ]
        return TimelineEntrySerializer(entries, many=True).data
