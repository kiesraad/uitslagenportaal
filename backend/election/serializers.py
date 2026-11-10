from django.urls import reverse
from rest_framework import serializers

from election.models import (
    Contest,
    ElectionConfig,
    ElectionDocument,
    TimelineDate,
)
from mainsite.models import RegionCategory
from mainsite.serializers import (
    ElectionSummarySerializer,
    RegionSummarySerializer,
)
from region.models import Region


class ElectionDocumentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    storage_key = serializers.CharField(read_only=True)
    content_type = serializers.CharField(read_only=True)
    size = serializers.IntegerField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    correction_number = serializers.IntegerField(read_only=True)
    metadata = serializers.JSONField(read_only=True)

    class Meta:
        model = ElectionDocument
        fields = (
            "url",
            "storage_key",
            "content_type",
            "size",
            "file_type",
            "correction_number",
            "metadata",
        )

    @staticmethod
    def get_url(obj: ElectionDocument) -> str:
        return reverse("document-download", kwargs={"pk": obj.pk})


class TimelineDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineDate
        fields = (
            "event",
            "date",
            "qualifier",
        )


class ElectionConfigSerializer(serializers.ModelSerializer):
    timeline_dates = TimelineDateSerializer(many=True, read_only=True)
    single_csb = serializers.SerializerMethodField()

    class Meta:
        model = ElectionConfig
        fields = (
            "slug",
            "label",
            "date",
            "issue_report_opens_at",
            "issue_report_deadline",
            "timeline_dates",
            "csb_type",
            "single_csb",
            "has_hsb",
            "report_error_url",
            "counting_info_url",
            "voting_url",
        )

    def get_single_csb(self, obj):
        """The CSB region for categories whose CSB is the staat (TK, EP), so the frontend can skip the CSB list.
        Decided by category.
        """
        if obj.csb_type != RegionCategory.STAAT:
            return None
        return (
            Region.objects.filter(election__election_config=obj, region_category=RegionCategory.STAAT)
            .values("region_name", "slug")
            .first()
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
        fields = ("id", "identifier", "name", "election", "region")
