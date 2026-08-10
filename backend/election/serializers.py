from django.utils import timezone
from rest_framework import serializers

from election.models import (
    Contest,
    ElectionConfig,
    ElectionDocument,
    TimelineEntry,
    TimelineEntryStatus,
    TimelineVariant,
)
from mainsite.serializers import (
    ElectionSummarySerializer,
    RegionSummarySerializer,
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
    status = serializers.SerializerMethodField()

    class Meta:
        model = TimelineEntry
        fields = (
            "status",
            "title",
            "date",
            "body",
        )

    def get_status(self, obj):
        now = timezone.localtime(timezone.now())
        entry_date = timezone.localtime(obj.date)

        if entry_date.date() == now.date():
            return TimelineEntryStatus.IN_PROGRESS
        elif entry_date.date() < now.date():
            return TimelineEntryStatus.DONE
        else:
            return TimelineEntryStatus.PENDING


class ElectionConfigSerializer(serializers.ModelSerializer):
    timeline_entries = serializers.SerializerMethodField()

    class Meta:
        model = ElectionConfig
        fields = (
            "slug",
            "label",
            "date",
            "issue_report_opens_at",
            "issue_report_deadline",
            "timeline_entries",
            "csb_type",
            "report_error_url",
            "counting_info_url",
            "voting_url",
        )

    def get_timeline_entries(self, obj):
        entries = [entry for entry in obj.timeline_entries.all() if entry.variant == TimelineVariant.DEFAULT]
        return TimelineEntrySerializer(entries, many=True).data


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
