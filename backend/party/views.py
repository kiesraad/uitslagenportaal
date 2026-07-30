from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from election.models import VoteCount
from mainsite.models import RegionCategory
from mainsite.serializers import CandidateSummarySerializer
from party.models import Party
from party.serializers import PartyDetailSerializer, PartyListSerializer
from region.models import Region


class PartyResultMatrixView(APIView):
    def get(self, request):
        election_slug = request.query_params.get("election")
        party_slug = request.query_params.get("party")
        csb_slug = request.query_params.get("csb")

        if not election_slug:
            raise ValidationError({"election": "This query parameter is required."})
        if not party_slug:
            raise ValidationError({"party": "This query parameter is required."})
        if not csb_slug:
            raise ValidationError({"csb": "This query parameter is required."})

        try:
            party = Party.objects.get(
                slug=party_slug,
                election__slug=election_slug,
            )
        except Party.DoesNotExist:
            raise ValidationError({"party": "Party not found for this election."})

        try:
            csb = Region.objects.get(
                slug=csb_slug,
                election__slug=election_slug,
            )
        except Region.DoesNotExist:
            raise ValidationError({"csb": "CSB not found for this election."})

        gemeentes = list(
            Region.objects.filter(
                election=csb.election,
                region_category=RegionCategory.GEMEENTE,
                parent__parent=csb,
            ).order_by("region_name")
        )
        candidates = list(party.candidates.order_by("position"))

        vote_counts = VoteCount.objects.filter(
            party=party,
            region__in=[csb, *gemeentes],
            eml_type="510d",
        )
        votes_by_candidate_and_region = {
            (vote_count.candidate_id, vote_count.region_id): vote_count.valid_votes
            for vote_count in vote_counts
            if vote_count.result_level == VoteCount.RESULT_LEVEL_CANDIDATE
        }
        party_votes_by_region = {
            vote_count.region_id: vote_count.valid_votes
            for vote_count in vote_counts
            if vote_count.result_level == VoteCount.RESULT_LEVEL_PARTY
        }

        rows = []
        for candidate in candidates:
            rows.append(
                {
                    "candidate": CandidateSummarySerializer(candidate).data,
                    "total": votes_by_candidate_and_region.get((candidate.id, csb.id)),
                    "votes": {
                        gemeente.slug: votes_by_candidate_and_region.get((candidate.id, gemeente.id))
                        for gemeente in gemeentes
                    },
                }
            )

        return Response(
            {
                "party": {"registered_name": party.registered_name, "slug": party.slug},
                "csb": {"region_name": csb.region_name, "slug": csb.slug},
                "columns": [{"slug": gemeente.slug, "region_name": gemeente.region_name} for gemeente in gemeentes],
                "rows": rows,
                "totals": {
                    "total": party_votes_by_region.get(csb.id),
                    "votes": {
                        gemeente.slug: party_votes_by_region.get(gemeente.id) for gemeente in gemeentes
                    },
                },
            }
        )


class PartyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Party.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.select_related("election")
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PartyDetailSerializer
        return PartyListSerializer
