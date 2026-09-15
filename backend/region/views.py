from django.db.models import Prefetch
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView

from election.models import ElectionDocument, VoteCount, VoterTurnoutCount
from election.utils import visibility_cutoff
from mainsite.models import RegionCategory
from mainsite.utils.eml_type import EML_TYPE_BY_REPORTING_LEVEL, EmlType, ReportingLevel
from region.models import Region
from region.serializers import RegionDetailSerializer, RegionListSerializer

_OWN_RESULTS_EML_TYPE = {
    RegionCategory.GEMEENTE: EmlType.EML_510b,
    RegionCategory.KIESKRING: EmlType.EML_510c,
}

# FileType values are EML510b, not the EmlType strings 510b used on vote counts.
_DOCUMENT_FILE_TYPE_BY_REPORTING_LEVEL = {
    ReportingLevel.GSB: ElectionDocument.FileType.EML_510B,
    ReportingLevel.HSB: ElectionDocument.FileType.EML_510C,
    ReportingLevel.CSB: ElectionDocument.FileType.EML_510D,
}


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

        # optional — only regions that published their own results (see _OWN_RESULTS_EML_TYPE)
        has_own_results = self.request.query_params.get("has_own_results") == "true"

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
        if has_own_results:
            own_eml_type = _OWN_RESULTS_EML_TYPE.get(region_category)
            if own_eml_type is None:
                raise ValidationError({"has_own_results": f"Not supported for region_category {region_category}."})
            result = result.filter(vote_counts__eml_type=own_eml_type).distinct()
        return result


class RegionDetailView(RetrieveAPIView):
    serializer_class = RegionDetailSerializer

    def get_object(self):
        election_config_slug = self.request.query_params.get("election_config")
        region_slug = self.request.query_params.get("region")
        level = self.request.query_params.get("level")
        # optional
        csb_slug = self.request.query_params.get("csb")
        parent_region_slug = self.request.query_params.get("parent_region")

        if not election_config_slug:
            raise ValidationError({"election_config": "This query parameter is required."})
        if not region_slug:
            raise ValidationError({"region": "This query parameter is required."})
        if level not in ReportingLevel.values:
            raise ValidationError({"level": "This query parameter is required and must be gsb, hsb, or csb."})

        eml_type = EML_TYPE_BY_REPORTING_LEVEL[level]
        document_file_type = _DOCUMENT_FILE_TYPE_BY_REPORTING_LEVEL[level]
        queryset = (
            Region.objects.select_related(
                "csb",
                "election__election_config",
            )
            .prefetch_related(
                Prefetch(
                    "vote_counts",
                    queryset=VoteCount.objects.filter(eml_type=eml_type).select_related("party", "candidate"),
                ),
                Prefetch(
                    "voter_turnout_counts",
                    queryset=VoterTurnoutCount.objects.filter(eml_type=eml_type),
                ),
                # ElectionDocument uses CurrentManager; explicit Prefetch ensures prefetched
                # rows match obj.documents.all(), not all_objects.
                Prefetch("documents", queryset=ElectionDocument.objects.filter(file_type=document_file_type)),
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
            raise NotFound({"detail": "Region not found for this election."})
        except Region.MultipleObjectsReturned:
            raise ValidationError(
                {"detail": "Multiple regions match this slug. Specify the 'parent_region' or 'csb' query parameter."}
            )
