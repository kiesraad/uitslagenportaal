from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView

from mainsite.models import RegionCategory
from region.models import Region
from region.serializers import RegionListSerializer, RegionDetailSerializer


class RegionListView(ListAPIView):
    serializer_class = RegionListSerializer

    def get_queryset(self):
        election_config_slug = self.request.query_params.get("election_config")
        if not election_config_slug:
            raise ValidationError(
                {"election_config": "This query parameter is required."}
            )

        # optional
        region_category = self.request.query_params.get("region_category")

        # optional
        region_slug = self.request.query_params.get("parent_region")

        if region_category:
            if region_category not in RegionCategory.values:
                raise ValidationError(
                    {f"region_category {region_category} not recognized."}
                )
        if not (region_category or region_slug):
            raise ValidationError({f"Either region_category or region_slug needed"})

        result = Region.objects.filter(
            election__election_config__slug=election_config_slug,
        ).order_by("region_name")
        if region_slug:
            result = result.filter(parent__slug=region_slug)
        if region_category:
            result = result.filter(region_category=region_category)
        return result


class RegionDetailView(RetrieveAPIView):
    serializer_class = RegionDetailSerializer

    def get_object(self):
        election_config_slug = self.request.query_params.get("election_config")
        region_slug = self.request.query_params.get("region")

        if not election_config_slug:
            raise ValidationError(
                {"election_config": "This query parameter is required."}
            )
        if not region_slug:
            raise ValidationError({"region": "This query parameter is required."})

        try:
            return Region.objects.select_related(
                "parent",
                "election__election_config",
            ).prefetch_related(
                "vote_counts__party",
                "vote_counts__candidate",
                "voter_turnout_counts",
                "election__election_config__timeline_entries",
            ).get(
                election__election_config__slug=election_config_slug,
                slug=region_slug,
            )
        except Region.DoesNotExist:
            raise ValidationError({"detail": "Region not found for this election."})
