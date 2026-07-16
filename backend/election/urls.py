from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import ContestViewSet, ElectionConfigViewSet, download_document

router = DefaultRouter()
router.register("election_configs", ElectionConfigViewSet, basename="election_configs")
router.register("contests", ContestViewSet, basename="contest")


urlpatterns = [
    path(
        "documents/<int:pk>/download/",
        download_document,
        name="document-download",
    ),
    *router.urls,
]
