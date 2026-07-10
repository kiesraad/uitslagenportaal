from rest_framework.routers import DefaultRouter

from .views import ContestViewSet, ElectionConfigViewSet

router = DefaultRouter()
router.register("election_configs", ElectionConfigViewSet, basename="election_configs")
router.register("contests", ContestViewSet, basename="contest")

urlpatterns = router.urls
