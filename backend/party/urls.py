from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CSBPartyResultMatrixView, HSBPartyResultMatrixView, PartyViewSet

router = DefaultRouter()
router.register("parties", PartyViewSet, basename="party")

urlpatterns = [
    path("party-result-matrix/", CSBPartyResultMatrixView.as_view(), name="party-result-matrix"),
    path("hsb-party-result-matrix/", HSBPartyResultMatrixView.as_view(), name="hsb-party-result-matrix"),
    *router.urls,
]
