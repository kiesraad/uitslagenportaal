from django.urls import path

from .views import RegionDetailView, RegionListView

urlpatterns = [
    path("region/", RegionDetailView.as_view(), name="region-detail"),
    path("regions/", RegionListView.as_view(), name="region-list"),
]
