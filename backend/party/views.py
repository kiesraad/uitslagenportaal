from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from election.models import Contest, VoteCount
from election.utils import visibility_cutoff
from mainsite.models import RegionCategory
from mainsite.serializers import CandidateSummarySerializer
from mainsite.utils.eml_type import EmlType
from party.models import Party
from party.serializers import PartyDetailSerializer, PartyListSerializer
from region.models import Region


def _resolve_party(party_slug: str, election_slug: str, cutoff) -> Party:
    try:
        return Party.objects.get(
            slug=party_slug,
            election__slug=election_slug,
            election__election_config__date__gte=cutoff,
        )
    except Party.DoesNotExist:
        raise NotFound({"party": "Party not found for this election."})


def _preferred_eml_type(region: Region, preferred: str) -> str:
    has_own_results = VoteCount.objects.filter(region=region, eml_type=preferred).exists()
    return preferred if has_own_results else EmlType.EML_510d


def _build_matrix_response(
    *,
    party: Party,
    region: Region,
    children: list[Region],
    region_key: str,
    eml_type: str,
    contest_id: int | None = None,
) -> Response:
    candidate_qs = party.candidates.filter(contest_id=contest_id) if contest_id is not None else party.candidates
    candidates = list(candidate_qs.order_by("position"))

    vote_counts = VoteCount.objects.filter(
        party=party,
        region__in=[region, *children],
        eml_type=eml_type,
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
                "total": votes_by_candidate_and_region.get((candidate.id, region.id)),
                "votes": {
                    child.slug: votes_by_candidate_and_region.get((candidate.id, child.id)) for child in children
                },
            }
        )

    return Response(
        {
            "party": {"registered_name": party.registered_name, "slug": party.slug},
            region_key: {"region_name": region.region_name, "slug": region.slug},
            "columns": [{"slug": child.slug, "region_name": child.region_name} for child in children],
            "rows": rows,
            "totals": {
                "total": party_votes_by_region.get(region.id),
                "votes": {child.slug: party_votes_by_region.get(child.id) for child in children},
            },
        }
    )


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
        # Expired elections are hidden everywhere
        cutoff = visibility_cutoff()

        party = _resolve_party(party_slug, election_slug, cutoff)

        try:
            csb = Region.objects.get(
                slug=csb_slug,
                election__slug=election_slug,
                election__election_config__date__gte=cutoff,
            )
        except Region.DoesNotExist:
            raise NotFound({"csb": "CSB not found for this election."})

        gemeentes = list(
            Region.objects.filter(
                election=csb.election,
                region_category=RegionCategory.GEMEENTE,
                csb=csb,
            ).order_by("region_name")
        )

        return _build_matrix_response(
            party=party,
            region=csb,
            children=gemeentes,
            region_key="csb",
            eml_type=EmlType.EML_510d,
        )


class HSBPartyResultMatrixView(APIView):
    def get(self, request):
        election_slug = request.query_params.get("election")
        party_slug = request.query_params.get("party")
        hsb_slug = request.query_params.get("hsb")

        if not election_slug:
            raise ValidationError({"election": "This query parameter is required."})
        if not party_slug:
            raise ValidationError({"party": "This query parameter is required."})
        if not hsb_slug:
            raise ValidationError({"hsb": "This query parameter is required."})
        # Expired elections are hidden everywhere
        cutoff = visibility_cutoff()

        party = _resolve_party(party_slug, election_slug, cutoff)

        try:
            kieskring = Region.objects.get(
                slug=hsb_slug,
                region_category=RegionCategory.KIESKRING,
                election__slug=election_slug,
                election__election_config__date__gte=cutoff,
            )
        except Region.DoesNotExist:
            raise NotFound({"hsb": "Kieskring not found for this election."})

        gemeentes = list(
            Region.objects.filter(
                election=kieskring.election,
                region_category=RegionCategory.GEMEENTE,
                parent=kieskring,
            ).order_by("region_name")
        )
        contest = Contest.objects.filter(election=kieskring.election, name=kieskring.region_name).first()

        return _build_matrix_response(
            party=party,
            region=kieskring,
            children=gemeentes,
            region_key="hsb",
            eml_type=_preferred_eml_type(kieskring, EmlType.EML_510c),
            contest_id=contest.id if contest else None,
        )


class PartyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Party.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().filter(election__election_config__date__gte=visibility_cutoff())
        if self.action == "retrieve":
            queryset = queryset.select_related("election")
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PartyDetailSerializer
        return PartyListSerializer
