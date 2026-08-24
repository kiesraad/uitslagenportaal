from django.db.models import Prefetch
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView

from election.models import ElectionDocument, VoteCount, VoterTurnoutCount
from election.utils import visibility_cutoff
from mainsite.models import RegionCategory
from region.models import Region
from region.serializers import RegionDetailSerializer, RegionListSerializer


class RegionListView(ListAPIView):
    serializer_class = RegionListSerializer

    def get_queryset(self):
        election_config_slug = self.request.query_params.get("election_config")
        if not election_config_slug:
            raise ValidationError({"election_config": "This query parameter is required."})

        # optional
        region_category = self.request.query_params.get("region_category")

        # optional — direct parent slug
        parent_region_slug = self.request.query_params.get("parent_region")

        # optional — CSB ancestor slug (any depth)
        csb_slug = self.request.query_params.get("csb")

        if region_category:
            if region_category not in RegionCategory.values:
                raise ValidationError({f"region_category {region_category} not recognized."})
        if not (region_category or parent_region_slug or csb_slug):
            raise ValidationError({"Either region_category, parent_region, or csb needed"})

        result = (
            Region.objects.filter(
                election__election_config__slug=election_config_slug,
                # Expired elections are hidden everywhere, not just on the home page.
                election__election_config__date__gte=visibility_cutoff(),
            )
            .select_related("csb")
            .order_by("region_name")
        )
        if parent_region_slug:
            result = result.filter(parent__slug=parent_region_slug)
        if csb_slug:
            result = result.filter(csb__slug=csb_slug)
        if region_category:
            result = result.filter(region_category=region_category)
        return result


class RegionDetailView(RetrieveAPIView):
    serializer_class = RegionDetailSerializer

    def get_object(self):
        election_config_slug = self.request.query_params.get("election_config")
        region_slug = self.request.query_params.get("region")
        # optional
        csb_slug = self.request.query_params.get("csb")
        parent_region_slug = self.request.query_params.get("parent_region")

        if not election_config_slug:
            raise ValidationError({"election_config": "This query parameter is required."})
        if not region_slug:
            raise ValidationError({"region": "This query parameter is required."})

        queryset = (
            Region.objects.select_related(
                "csb",
                "election__election_config",
            )
            .prefetch_related(
                # VoteCount/VoterTurnoutCount.objects are current-only (CurrentManager).
                Prefetch(
                    "vote_counts",
                    queryset=VoteCount.objects.select_related("party", "candidate"),
                ),
                Prefetch("voter_turnout_counts", queryset=VoterTurnoutCount.objects.all()),
                Prefetch("documents", queryset=ElectionDocument.objects.all()),
                "election__election_config__timeline_entries",
            )
            .filter(
                election__election_config__slug=election_config_slug,
                election__election_config__date__gte=visibility_cutoff(),
                slug=region_slug,
            )
        )
        if parent_region_slug:
            queryset = queryset.filter(parent__slug=parent_region_slug)
        if csb_slug:
            queryset = queryset.filter(csb__slug=csb_slug)

        try:
            return queryset.get()
        except Region.DoesNotExist:
            raise ValidationError({"detail": "Region not found for this election."})
        except Region.MultipleObjectsReturned:
            raise ValidationError(
                {"detail": "Multiple regions match this slug. Specify the 'parent_region' or 'csb' query parameter."}
            )
