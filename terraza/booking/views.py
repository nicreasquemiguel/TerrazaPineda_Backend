from django.db.utils import IntegrityError
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters
from rest_framework.views import APIView, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from rest_framework.decorators import action

from .filters import BookingFilter
from .models import Booking, ExtraService, Venue, Package, BookingWish, Notification, Review
from .serializers import BookingSerializer, ExtraServiceSerializer, PackageSerializer, VenueSerializer, BookingCreateSerializer, BookingUpdateSerializer, BookingWishSerializer, NotificationSerializer, ReviewSerializer
from .serializers import BookingListSerializer

# Import logging utilities
try:
    from logs.utils import log_booking_created, log_booking_status_change, log_activity
except ImportError:
    # Fallback if logs app is not available
    def log_booking_created(*args, **kwargs):
        pass
    def log_booking_status_change(*args, **kwargs):
        pass
    def log_activity(*args, **kwargs):
        pass

class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Staff can view/edit all
        if request.user.is_staff:
            return True
        # Users can only view/edit their own bookings
        return obj.user == request.user

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
    filter_backends = [
        DjangoFilterBackend,
        drf_filters.OrderingFilter,
    ]
    filterset_class = BookingFilter
    
    ordering_fields = ['start_datetime', 'end_datetime', 'created_at', 'total_price']
    ordering = ['start_datetime']  # default ordering

    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Booking.objects.all()
        return Booking.objects.filter(user=user)

    def perform_create(self, serializer):
        # The BookingCreateSerializer already handles user assignment
        booking = serializer.save()
        # Log the booking creation
        try:
            log_booking_created(booking, self.request.user, self.request)
            log_activity(
                user=self.request.user,
                category='booking',
                action='created',
                description=f'Nueva reserva creada para {booking.venue.name} el {booking.start_datetime.date()}',
                request=self.request
            )
        except Exception as e:
            print(f"Failed to log booking creation: {e}")

    def perform_update(self, serializer):
        # Store old instance data before updating
        old_instance = self.get_object()
        old_data = {
            'status': old_instance.status,
            'package': old_instance.package,
            'start_datetime': old_instance.start_datetime,
            'end_datetime': old_instance.end_datetime,
            'total_price': old_instance.total_price,
            'advance_paid': old_instance.advance_paid,
            'description': old_instance.description,
            'extra_services': list(old_instance.extra_services.all()),
            'venue': old_instance.venue,
        }
        
        # Update the booking
        booking = serializer.save()
        
        # Track all changes
        changes = []
        
        # Check status changes
        if old_data['status'] != booking.status:
            try:
                log_booking_status_change(booking, self.request.user, old_data['status'], booking.status, self.request)
                changes.append(f"Estado: {old_data['status']} → {booking.status}")
            except Exception as e:
                print(f"Failed to log booking status change: {e}")
        
        # Check package changes
        if old_data['package'] != booking.package:
            changes.append(f"Paquete: {old_data['package'].title} → {booking.package.title}")
        
        # Check date changes
        if old_data['start_datetime'] != booking.start_datetime:
            changes.append(f"Fecha inicio: {old_data['start_datetime'].strftime('%Y-%m-%d %H:%M')} → {booking.start_datetime.strftime('%Y-%m-%d %H:%M')}")
        
        if old_data['end_datetime'] != booking.end_datetime:
            changes.append(f"Fecha fin: {old_data['end_datetime'].strftime('%Y-%m-%d %H:%M')} → {booking.end_datetime.strftime('%Y-%m-%d %H:%M')}")
        
        # Check price changes
        if old_data['total_price'] != booking.total_price:
            changes.append(f"Precio total: ${old_data['total_price']} → ${booking.total_price}")
        
        if old_data['advance_paid'] != booking.advance_paid:
            changes.append(f"Adelanto pagado: ${old_data['advance_paid']} → ${booking.advance_paid}")
        
        # Check description changes
        if old_data['description'] != booking.description:
            old_desc = old_data['description'] or "Sin descripción"
            new_desc = booking.description or "Sin descripción"
            changes.append(f"Descripción: {old_desc[:50]}... → {new_desc[:50]}...")
        
        # Check venue changes
        if old_data['venue'] != booking.venue:
            changes.append(f"Lugar: {old_data['venue'].name} → {booking.venue.name}")
        
        # Check extra services changes
        old_extras = set(old_data['extra_services'])
        new_extras = set(booking.extra_services.all())
        
        if old_extras != new_extras:
            old_extra_names = [extra.name for extra in old_extras]
            new_extra_names = [extra.name for extra in new_extras]
            changes.append(f"Servicios extra: {', '.join(old_extra_names) or 'Ninguno'} → {', '.join(new_extra_names) or 'Ninguno'}")
        
        # Log all changes
        if changes:
            try:
                # Log detailed changes
                log_activity(
                    user=self.request.user,
                    category='booking',
                    action='updated',
                    description=f'Reserva {booking.id} fue actualizada: {"; ".join(changes)}',
                    request=self.request,
                    metadata={
                        'booking_id': str(booking.id),
                        'venue_name': booking.venue.name,
                        'changes': changes,
                        'old_data': {
                            'status': old_data['status'],
                            'package': old_data['package'].title,
                            'start_datetime': old_data['start_datetime'].isoformat(),
                            'end_datetime': old_data['end_datetime'].isoformat(),
                            'total_price': str(old_data['total_price']),
                            'advance_paid': str(old_data['advance_paid']),
                            'venue': old_data['venue'].name,
                            'extra_services': [extra.name for extra in old_data['extra_services']]
                        },
                        'new_data': {
                            'status': booking.status,
                            'package': booking.package.title,
                            'start_datetime': booking.start_datetime.isoformat(),
                            'end_datetime': booking.end_datetime.isoformat(),
                            'total_price': str(booking.total_price),
                            'advance_paid': str(booking.advance_paid),
                            'venue': booking.venue.name,
                            'extra_services': [extra.name for extra in booking.extra_services.all()]
                        }
                    }
                )
                
                # Also log specific changes using specialized functions
                from logs.utils import (
                    log_booking_activity, log_booking_extra_services_change,
                    log_booking_package_change, log_booking_date_change,
                    log_booking_price_change
                )
                
                # Log extra services changes specifically
                if old_data['extra_services'] != list(booking.extra_services.all()):
                    log_booking_extra_services_change(
                        booking, self.request.user, 
                        old_data['extra_services'], 
                        list(booking.extra_services.all()), 
                        self.request
                    )
                
                # Log package changes specifically
                if old_data['package'] != booking.package:
                    log_booking_package_change(
                        booking, self.request.user,
                        old_data['package'], booking.package,
                        self.request
                    )
                
                # Log date changes specifically
                if (old_data['start_datetime'] != booking.start_datetime or 
                    old_data['end_datetime'] != booking.end_datetime):
                    log_booking_date_change(
                        booking, self.request.user,
                        old_data['start_datetime'], old_data['end_datetime'],
                        booking.start_datetime, booking.end_datetime,
                        self.request
                    )
                
                # Log price changes specifically
                if (old_data['total_price'] != booking.total_price or 
                    old_data['advance_paid'] != booking.advance_paid):
                    log_booking_price_change(
                        booking, self.request.user,
                        old_data['total_price'], booking.total_price,
                        old_data['advance_paid'], booking.advance_paid,
                        self.request
                    )
                
                # Log general booking activity
                log_booking_activity(
                    user=self.request.user,
                    booking_id=booking.id,
                    action='updated',
                    old_status=old_data['status'],
                    new_status=booking.status,
                    description=f'Reserva actualizada con {len(changes)} cambios',
                    metadata={
                        'changes': changes,
                        'old_data': {
                            'status': old_data['status'],
                            'package': old_data['package'].title,
                            'total_price': str(old_data['total_price']),
                            'venue': old_data['venue'].name
                        },
                        'new_data': {
                            'status': booking.status,
                            'package': booking.package.title,
                            'total_price': str(booking.total_price),
                            'venue': booking.venue.name
                        }
                    }
                )
                
            except Exception as e:
                print(f"Failed to log booking update: {e}")
        else:
            # No changes detected, log basic update
            try:
                log_activity(
                    user=self.request.user,
                    category='booking',
                    action='updated',
                    description=f'Reserva {booking.id} fue actualizada (sin cambios detectados)',
                    request=self.request
                )
            except Exception as e:
                print(f"Failed to log booking update: {e}")

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        elif self.action == 'create':
            return BookingCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BookingUpdateSerializer
        return BookingSerializer



    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            return response
        except IntegrityError as e:
            if 'booking_event_slug_key' in str(e):
                return Response(
                    {"detail": "A booking with this slug already exists."},
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"detail": f"Database constraint error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
from rest_framework import viewsets, permissions
from .models import Package, ExtraService
from .serializers import PackageSerializer, ExtraServiceSerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAdminOrReadOnly]

class ExtraServiceViewSet(viewsets.ModelViewSet):
    queryset = ExtraService.objects.all()
    serializer_class = ExtraServiceSerializer
    permission_classes = [IsAdminOrReadOnly]

class BookingStatusCountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        # Only show the user's own bookings unless staff
        if user.is_staff:
            qs = Booking.objects.all()
        else:
            qs = Booking.objects.filter(user=user)
        status_counts = {status[0]: 0 for status in Booking.STATUS_CHOICES}
        for status, _ in Booking.STATUS_CHOICES:
            status_counts[status] = qs.filter(status=status).count()
        return Response(status_counts)

class BookedDatesView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        venue_id = request.query_params.get('venue')
        qs = Booking.objects.exclude(status__in=['cancelado', 'rechazado'])
        if venue_id:
            qs = qs.filter(venue_id=venue_id)
        # Debug: Print the actual start_datetime values
        for booking in qs:
            print(f"Booking {booking.id}: start_datetime={booking.start_datetime}, date={booking.start_datetime.date()}")
        booked = [
            {
                'date': booking.start_datetime.date().isoformat(),
                'user_initials': self.get_user_initials(booking.user),
            }
            for booking in qs
        ]
        return Response(booked)

    def get_user_initials(self, user):
        if user.first_name and user.last_name:
            return f"{user.first_name[0]}{user.last_name[0]}".upper()
        elif user.first_name:
            return user.first_name[0].upper()
        elif user.last_name:
            return user.last_name[0].upper()
        else:
            return "U"  # Unknown user


# Removed redundant views - BookedDatesView already handles availability

class BookingWishViewSet(viewsets.ModelViewSet):
    queryset = BookingWish.objects.all()
    serializer_class = BookingWishSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users see only their own wishes unless staff, and only from today onward
        user = self.request.user
        today = timezone.now().date()
        qs = BookingWish.objects.filter(wished_start_datetime__date__gte=today)
        if user.is_staff:
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_update(self, serializer):
        serializer.save()

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Review.objects.all()
        return Review.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get", "put"], url_path=r"me-by-booking/(?P<booking_id>[0-9a-f\-]{36})")
    def me_by_booking(self, request, booking_id: str):
        # Ensure user can access the booking
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff and booking.user_id != request.user.id:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        # Fetch or create/update the user's review for this booking
        if request.method == "GET":
            try:
                review = Review.objects.get(booking=booking, user=request.user)
            except Review.DoesNotExist:
                return Response({"detail": "No review yet"}, status=status.HTTP_404_NOT_FOUND)
            return Response(self.get_serializer(review).data)

        # PUT upsert
        try:
            review = Review.objects.get(booking=booking, user=request.user)
            serializer = self.get_serializer(review, data=request.data, partial=False)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(user=request.user)
        except Review.DoesNotExist:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save(user=request.user, booking=booking)
        return Response(self.get_serializer(instance).data)