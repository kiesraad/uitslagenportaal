from rest_framework import serializers

from election.models import Contest, ElectionStep, ElectionConfig
from mainsite.serializers import (
    RegionSummarySerializer,
    ElectionSummarySerializer,
)

class ElectionStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectionStep
        fields = (
            "position",
            "state",
            "title",
            "date",
            "body",
        )


class ElectionConfigSerializer(serializers.ModelSerializer):
    steps = ElectionStepSerializer(many=True, read_only=True)

    class Meta:
        model = ElectionConfig
        fields = (
            "slug",
            "label",
            "date",
            'steps'
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

