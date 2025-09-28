from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActivityLogViewSet, BookingLogViewSet, PaymentLogViewSet,
    UserActivityLogViewSet, SystemLogViewSet, AuditLogViewSet
)

router = DefaultRouter()
router.register('activity', ActivityLogViewSet, basename='activity-logs')
router.register('booking', BookingLogViewSet, basename='booking-logs')
router.register('payment', PaymentLogViewSet, basename='payment-logs')
router.register('user', UserActivityLogViewSet, basename='user-logs')
router.register('system', SystemLogViewSet, basename='system-logs')
router.register('audit', AuditLogViewSet, basename='audit-logs')

urlpatterns = [
    path('', include(router.urls)),
]
