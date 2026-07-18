from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import AdminSmartDeviceViewSet, ClientSmartDeviceViewSet

router = SimpleRouter()
router.register('devices', AdminSmartDeviceViewSet, basename='admin-smart-device')
router.register('my-devices', ClientSmartDeviceViewSet, basename='client-smart-device')

urlpatterns = [
    path('', include(router.urls)),
]
