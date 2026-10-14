from django.urls import path

from .views import RegionDetailView, RegionListView, polling_station_pv_archive

urlpatterns = [
    path("", RegionListView.as_view(), name="region-list"),
    path("<slug:region>/polling-station-pvs.zip", polling_station_pv_archive, name="polling-station-pv-archive"),
    path("<slug:region>", RegionDetailView.as_view(), name="region-detail"),
]
