from rest_framework import viewsets

from election.models import Contest, ElectionConfig
from election.serializers import (
    ContestDetailSerializer,
    ContestListSerializer,
    ElectionConfigSerializer,
)

class ElectionConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ElectionConfig.objects.all()
    lookup_field = "slug"

    def get_serializer_class(self):
        return ElectionConfigSerializer


class ContestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Contest.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.select_related(
                "election",
                "region",
            ).prefetch_related("candidate_lists")
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ContestDetailSerializer
        return ContestListSerializer

