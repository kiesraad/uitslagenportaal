from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ContestViewSet, ElectionConfigViewSet, certified_document_preview, download_document

router = DefaultRouter()
router.register("election_configs", ElectionConfigViewSet, basename="election_configs")
router.register("contests", ContestViewSet, basename="contest")


urlpatterns = [
    path(
        "documents/<int:pk>/download/",
        download_document,
        name="document-download",
    ),
    path(
        "certified-documents/<int:pk>/preview/",
        certified_document_preview,
        name="certified-document-preview",
    ),
    *router.urls,
]
