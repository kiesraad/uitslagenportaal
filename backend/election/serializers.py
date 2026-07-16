from rest_framework import serializers

from election.models import Contest, TimelineEntry, ElectionConfig, ElectionDocument
from mainsite.serializers import (
    RegionSummarySerializer,
    ElectionSummarySerializer,
)


class ElectionDocumentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    storage_key = serializers.CharField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)
    file_type = serializers.CharField(read_only=True)

    class Meta:
        model = ElectionDocument
        fields = (
            "url",
            "storage_key",
            "content_type",
            "size",
            "file_type",
        )

    def get_url(self, obj: ElectionDocument) -> str:
        request = self.context.get("request")
        path = f"/api/documents/{obj.pk}/download/"
        if request is not None:
            return request.build_absolute_uri(path)
        return path


class TimelineEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEntry
        fields = (
            "status",
            "title",
            "date",
            "body",
        )


class ElectionConfigSerializer(serializers.ModelSerializer):
    timeline_entries = TimelineEntrySerializer(many=True, read_only=True)

    class Meta:
        model = ElectionConfig
        fields = ("slug", "label", "date", "timeline_entries")


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
        fields = ("id", "identifier", "name", "election", "region")
