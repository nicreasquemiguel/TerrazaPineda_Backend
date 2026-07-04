from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    BookingViewSet,
    VenueViewSet,
    PackageViewSet,
    ExtraServiceViewSet,
    BookingStatusCountsView,
    BookedDatesView,
    BookingWishViewSet,
    NotificationViewSet,
    ReviewViewSet,
    VenueConfigurationView,
)

router = SimpleRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'venues', VenueViewSet, basename='venue')
router.register(r'packages', PackageViewSet, basename='package')
router.register(r'extras', ExtraServiceViewSet, basename='extraservice')
router.register(r'wishes', BookingWishViewSet, basename='bookingwish')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
    path('status-counts/', BookingStatusCountsView.as_view(), name='booking-status-counts'),
    path('booked-dates/', BookedDatesView.as_view(), name='booked-dates'),
    path('configuration/', VenueConfigurationView.as_view(), name='venue-configuration'),
]
