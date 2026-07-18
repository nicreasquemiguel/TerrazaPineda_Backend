from django.utils import timezone
from rest_framework.permissions import BasePermission

from booking.models import Booking

ACTIVE_BOOKING_STATUSES = [
    'aceptacion', 'apartado', 'liquidado', 'liquidado_entregado', 'entregado', 'finalizado',
]


class HasSameDayActiveBooking(BasePermission):
    """Allows access to a SmartDevice only if the requesting user has an active
    booking at that device's venue starting today."""

    def has_object_permission(self, request, view, obj):
        return Booking.objects.filter(
            venue=obj.venue,
            user=request.user,
            status__in=ACTIVE_BOOKING_STATUSES,
            start_date=timezone.now().date(),
        ).exists()
