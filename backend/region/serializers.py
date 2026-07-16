from rest_framework import serializers

from election.serializers import TimelineEntrySerializer, ElectionDocumentSerializer
from region.models import Region
from mainsite.models import RegionCategory
from mainsite.serializers import (
    VoteCountSummarySerializer,
    VoterTurnoutCountSummarySerializer,
)


class RegionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("region_name", "slug", "region_category")


class RegionDetailSerializer(serializers.ModelSerializer):

    voter_turnout_counts = VoterTurnoutCountSummarySerializer(many=True, read_only=True)
    vote_counts = serializers.SerializerMethodField()
    documents = ElectionDocumentSerializer(many=True, read_only=True)
    # For now the timeline entries come from the region's election config, so
    # every region in an election shows the same entries. This will be refactored
    # to per-region entries later; the serializer field keeps the API stable.
    timeline_entries = TimelineEntrySerializer(
        source="election.election_config.timeline_entries",
        many=True,
        read_only=True,
    )

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
