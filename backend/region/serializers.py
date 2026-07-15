from rest_framework import serializers

from election.document_serializers import ElectionDocumentSerializer
from election.models import ElectionDocument
from election.serializers import TimelineEntrySerializer
from region.models import Region
from mainsite.models import RegionCategory
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
    documents = ElectionDocumentSerializer(many=True, read_only=True)
    # For now the timeline entries come from the region's election config, so
    # every region in an election shows the same entries. This will be refactored
    # to per-region entries later; the serializer field keeps the API stable.
    timeline_entries = TimelineEntrySerializer(
        source="election.election_config.timeline_entries",
        many=True,
        read_only=True,
    )

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
