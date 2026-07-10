from rest_framework import serializers

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

    class Meta:
        model = Region
        fields = ("voter_turnout_counts", "region_name", "vote_counts", "slug")
