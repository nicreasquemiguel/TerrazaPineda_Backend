from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, DashboardStatsViewSet

router = DefaultRouter()
router.register('dashboard', DashboardViewSet, basename='dashboard')
router.register('stats', DashboardStatsViewSet, basename='dashboard-stats')

urlpatterns = [
    path('', include(router.urls)),
] 