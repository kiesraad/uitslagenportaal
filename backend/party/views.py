from rest_framework import viewsets

from party.models import Party
from party.serializers import PartyDetailSerializer, PartyListSerializer


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
