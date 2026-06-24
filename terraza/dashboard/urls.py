from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import DashboardViewSet, DashboardStatsViewSet

router = SimpleRouter()
router.register('dashboard', DashboardViewSet, basename='dashboard')
router.register('stats', DashboardStatsViewSet, basename='dashboard-stats')

urlpatterns = [
    path('', include(router.urls)),
] 