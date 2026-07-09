from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from . import selectors as sel
from .serializers import (
    ElectionSerializer,
    RegionSerializer,
    PollingStationSerializer,
    UnitResultSerializer,
    CandidateVoteSerializer,
)
from .models import Election, PollingStation


class ElectionList(ListAPIView):
    serializer_class = ElectionSerializer

    def get_queryset(self):
        return Election.objects.filter(deleted_on__isnull=True).order_by(
            "category", "name"
        )


class ElectionDetail(APIView):
    def get(self, request, election_id):
        election = sel.get_election(election_id)
        return Response(ElectionSerializer(election).data)


class GemeenteList(ListAPIView):
    # GET list of gemeente alphabetically
    serializer_class = RegionSerializer

    def get_queryset(self):
        election = sel.get_election(self.kwargs["election_id"])
        parent = None
        parent_number = self.request.query_params.get("parent")
        if parent_number:
            parent = sel.get_region(election, parent_number)
        return sel.gemeenten_for(election, parent)


class KieskringGemeenteList(ListAPIView):
    # GET gemeente subset by kieskring
    # TODO: make more generic
    serializer_class = RegionSerializer

    def get_queryset(self):
        election = sel.get_election(self.kwargs["election_id"])
        parent = sel.get_region(election, self.kwargs["region_number"])
        return sel.gemeenten_for(election, parent)


class KieskringList(ListAPIView):
    # Get all kieskringen (if there are)
    serializer_class = RegionSerializer

    def get_queryset(self):
        election = sel.get_election(self.kwargs["election_id"])
        return (
            election.regions.filter(deleted_on__isnull=True)
            .exclude(category="GEMEENTE")
            .exclude(parent__isnull=True)
            .order_by("name")
        )


class StembureauList(ListAPIView):
    # GET all stembureaus alphabetically in municipality
    serializer_class = PollingStationSerializer

    def get_queryset(self):
        election = sel.get_election(self.kwargs["election_id"])
        gemeente = sel.get_region(
            election, self.kwargs["region_number"], category="GEMEENTE"
        )
        return gemeente.polling_stations.filter(deleted_on__isnull=True).order_by(
            "name"
        )


# TODO: improve implementation of returning no available data for frontend --> Different page
class GemeenteResult(APIView):
    # GET totals + party totals for Gemeente
    def get(self, request, election_id, region_number):
        election = sel.get_election(election_id)
        gemeente = sel.get_region(election, region_number, category="GEMEENTE")
        unit = sel.total_unit_for_region(gemeente)
        return Response(UnitResultSerializer.from_unit(unit).data)


class StembureauResult(APIView):
    # GET totals + party totals for Stembureau
    def get(self, request, election_id, sb_code):
        election = sel.get_election(election_id)
        station, unit = sel.polling_station_unit(election, sb_code)
        return Response(UnitResultSerializer.from_unit(unit).data)


class GemeentePartyCandidates(APIView):
    # GET candidate votes of party within gemeente
    def get(self, request, election_id, region_number, affiliation_id):
        election = sel.get_election(election_id)
        gemeente = sel.get_region(election, region_number, category="GEMEENTE")
        unit = sel.total_unit_for_region(gemeente)
        affiliation, votes = sel.candidate_votes_for(unit, affiliation_id)
        return Response(
            {
                "affiliation_id": affiliation.affiliation_id,
                "name": affiliation.name,
                "candidates": CandidateVoteSerializer(votes, many=True).data,
            }
        )


class StembureauPartyCandidates(APIView):
    # GET candidate votes of party within Stembureau
    def get(self, request, election_id, sb_code, affiliation_id):
        election = sel.get_election(election_id)
        station, unit = sel.polling_station_unit(election, sb_code)
        affiliation, votes = sel.candidate_votes_for(unit, affiliation_id)
        return Response(
            {
                "stembureau": station.name,
                "affiliation_id": affiliation.affiliation_id,
                "name": affiliation.name,
                "candidates": CandidateVoteSerializer(votes, many=True).data,
            }
        )


# TODO: Implement other levels of candidate votes/party votes or use abstraction
