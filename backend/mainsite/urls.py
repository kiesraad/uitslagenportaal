"""
URL configuration for Uitslagenportaal backend.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib.sitemaps import views as sitemap_views
from django.urls import include, path

from mainsite import views
from mainsite.sitemaps import sitemaps

urlpatterns = [
    path("api/", include("election.urls")),
    path("api/<str:election_config>/regions/", include("region.urls")),
    path("api/", include("party.urls")),
    path("api/report-technical-issue/", views.report_technical_issue, name="report-technical-issue"),
    path("sitemap.xml", sitemap_views.index, {"sitemaps": sitemaps, "sitemap_url_name": "sitemap-section"}),
    path("sitemap/<section>.xml", sitemap_views.sitemap, {"sitemaps": sitemaps}, name="sitemap-section"),
    # Neither of these is reachable from the internet: the Gateway routes only /api and /sitemap to
    # the backend and everything else to the frontend. Probes and metric scrapes come
    # from inside the cluster and address the pod directly.
    path("healthz/", views.healthz, name="healthz"),
    path("", include("django_prometheus.urls")),
]
