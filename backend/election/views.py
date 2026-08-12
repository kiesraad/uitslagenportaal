from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from election.models import Contest, ElectionConfig, ElectionDocument, visibility_cutoff
from election.serializers import (
    ContestDetailSerializer,
    ContestListSerializer,
    ElectionConfigSerializer,
)


class ElectionConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ElectionConfig.objects.all()
    lookup_field = "slug"

    def get_queryset(self):
        return super().get_queryset().filter(date__gte=visibility_cutoff())

    def get_serializer_class(self):
        return ElectionConfigSerializer


class ContestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Contest.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().filter(election__election_config__date__gte=visibility_cutoff())
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


def download_document(request, pk):
    document = get_object_or_404(
        ElectionDocument.objects.filter(
            Q(region__isnull=True) | Q(region__election__election_config__date__gte=visibility_cutoff()),
        ),
        pk=pk,
    )

    data_root = (settings.BASE_DIR / ".data").resolve()
    file_path = (data_root / document.storage_key).resolve()

    if not file_path.is_relative_to(data_root) or not file_path.is_file():
        raise Http404("Document not found")

    return FileResponse(
        file_path.open("rb"),
        content_type=document.content_type,
        as_attachment=True,
        filename=Path(document.storage_key).name,
    )
