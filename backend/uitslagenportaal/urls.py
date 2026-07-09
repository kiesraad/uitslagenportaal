from django.urls import path
from . import views

urlpatterns = [
    path("elections/", views.ElectionList.as_view()),
    path("elections/<str:election_id>/", views.ElectionDetail.as_view()),  # TK2023
    path("elections/<str:election_id>/gemeenten/", views.GemeenteList.as_view()),
    path("elections/<str:election_id>/kieskringen/", views.KieskringList.as_view()),
    path(
        "elections/<str:election_id>/kieskringen/<str:region_number>/gemeenten/",
        views.KieskringGemeenteList.as_view(),
    ),
    path(
        "elections/<str:election_id>/gemeenten/<str:region_number>/stembureaus/",
        views.StembureauList.as_view(),
    ),
    path(
        "elections/<str:election_id>/gemeenten/<str:region_number>/partijen/<int:affiliation_id>/",
        views.GemeentePartyCandidates.as_view(),
    ),
    path(
        "elections/<str:election_id>/stembureaus/<path:sb_code>/partijen/<int:affiliation_id>/",
        views.StembureauPartyCandidates.as_view(),
    ),
    # TODO: Add endpoints for Kieskring/HSB/CSB results
    # path("elections/<str:election_id>/gemeenten/<str:region_number>/", views.KieskringResult.as_view()),
    path(
        "elections/<str:election_id>/gemeenten/<str:region_number>/",
        views.GemeenteResult.as_view(),
    ),  # 0758
    # TODO: Review sb_code effectivity
    path(
        "elections/<str:election_id>/stembureaus/<path:sb_code>/",
        views.StembureauResult.as_view(),
    ),  # 0744::SB2
]
