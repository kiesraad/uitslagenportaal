from rest_framework import serializers

from election.models import Contest, TimelineEntry, ElectionConfig
from mainsite.serializers import (
    RegionSummarySerializer,
    ElectionSummarySerializer,
)

class TimelineEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEntry
        fields = (
            "position",
            "status",
            "title",
            "date",
            "body",
        )


class ElectionConfigSerializer(serializers.ModelSerializer):
    timeline_entries = TimelineEntrySerializer(many=True, read_only=True)

    class Meta:
        model = ElectionConfig
        fields = (
            "slug",
            "label",
            "date",
            'timeline_entries'
        )


class ContestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contest
        fields = (
            "id",
            "election_id",
            "region_id",
            "identifier",
            "subcategory",
            "name",
        )


class ContestDetailSerializer(serializers.ModelSerializer):
    election = ElectionSummarySerializer(read_only=True)
    region = RegionSummarySerializer(read_only=True, allow_null=True)
    candidate_lists = serializers.SerializerMethodField()

    class Meta:
        model = Contest
        fields = (
            "id",
            "identifier",
            "name",
            "election",
            "region"
        )

