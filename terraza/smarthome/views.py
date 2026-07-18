from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import SmartDevice
from .serializers import SmartDeviceSerializer, DeviceCommandSerializer
from .permissions import HasSameDayActiveBooking, ACTIVE_BOOKING_STATUSES
from .exceptions import TuyaAPIError
from . import tuya_client

try:
    from logs.utils import log_activity
except ImportError:
    def log_activity(*args, **kwargs):
        pass


class SmartDeviceControlMixin:
    """Shared control/status actions so admin and client surfaces hit the exact same Tuya logic."""

    @action(detail=True, methods=['post'])
    def control(self, request, pk=None):
        device = self.get_object()
        serializer = DeviceCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            if data['action'] == 'on':
                tuya_client.turn_device(device, True)
            elif data['action'] == 'off':
                tuya_client.turn_device(device, False)
            else:
                if not device.supports_color:
                    return Response({'error': 'This device does not support color.'}, status=status.HTTP_400_BAD_REQUEST)
                color = data['color']
                tuya_client.set_device_color(device, color['h'], color['s'], color['v'])
        except TuyaAPIError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        log_activity(
            user=request.user if request.user.is_authenticated else None,
            category='venue',
            action='smart_device_control',
            description=f"{data['action']} on device '{device.name}' at {device.venue.name}",
            metadata={'device_id': str(device.id), 'action': data['action']},
            request=request,
        )
        return Response({'success': True, 'action': data['action']})

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        device = self.get_object()
        try:
            result = tuya_client.get_device_status(device)
        except TuyaAPIError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'status': result})


class AdminSmartDeviceViewSet(SmartDeviceControlMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SmartDeviceSerializer
    permission_classes = [IsAdminUser]
    # A venue's device list is small and bounded (a handful of physical lights) —
    # unlike other list endpoints in this API, it should never be silently truncated
    # by the global PAGE_SIZE=5 default.
    pagination_class = None
    queryset = SmartDevice.objects.select_related('venue').filter(is_active=True)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['venue']


class ClientSmartDeviceViewSet(SmartDeviceControlMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SmartDeviceSerializer
    permission_classes = [IsAuthenticated, HasSameDayActiveBooking]
    pagination_class = None

    def get_queryset(self):
        today = timezone.now().date()
        return SmartDevice.objects.select_related('venue').filter(
            is_active=True,
            venue__bookings__user=self.request.user,
            venue__bookings__status__in=ACTIVE_BOOKING_STATUSES,
            venue__bookings__start_date=today,
        ).distinct()
