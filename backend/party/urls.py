from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PartyResultMatrixView, PartyViewSet

router = DefaultRouter()
router.register("parties", PartyViewSet, basename="party")

urlpatterns = [
    path("party-result-matrix/", PartyResultMatrixView.as_view(), name="party-result-matrix"),
    *router.urls,
]
