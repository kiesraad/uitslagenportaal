from pathlib import Path

from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from election.models import CertifiedElectionDocument, Contest, ElectionConfig, ElectionDocument
from election.serializers import (
    ContestDetailSerializer,
    ContestListSerializer,
    ElectionConfigSerializer,
)
from election.utils import visibility_cutoff


class ElectionConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ElectionConfig.objects.all()
    lookup_field = "slug"

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
        ElectionDocument.all_objects.filter(
            Q(region__isnull=True) | Q(region__election__election_config__date__gte=visibility_cutoff()),
        ),
        pk=pk,
    )

    if not default_storage.exists(document.storage_key):
        raise Http404("Document not found")

    # Instruct browser to download the file using content-disposition header
    return HttpResponseRedirect(
        default_storage.url(document.storage_key, parameters={"ResponseContentDisposition": "attachment"})
    )


def certified_document_preview(request, pk):
    document = get_object_or_404(
        CertifiedElectionDocument.objects.filter(
            region__election__election_config__date__gte=visibility_cutoff(),
        ),
        pk=pk,
    )
    preview_key = Path(document.storage_key).with_suffix(".png").as_posix()
    if not default_storage.exists(preview_key):
        raise Http404("Preview not found")

    return HttpResponseRedirect(default_storage.url(preview_key, parameters={"ResponseContentType": "image/png"}))
