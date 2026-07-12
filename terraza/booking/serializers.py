import datetime as dt_module
from .models import Booking, ExtraService, Package, Venue, BookingWish, Notification, Review, BookingLineItem, VenueConfiguration
from users.serializers import UserSerializer
from rest_framework import serializers


class BookingLineItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = BookingLineItem
        fields = ['id', 'item_type', 'description', 'unit_price', 'quantity', 'subtotal']

class VenueConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueConfiguration
        fields = ['open_time', 'close_time']


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'

class ExtraServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraService
        fields = ['id', 'name', 'price','icon']


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id', 'name', 'address']

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    staff = UserSerializer(read_only=True)
    package = PackageSerializer()
    venue = VenueSerializer()
    extra_services = ExtraServiceSerializer(many=True, required=False)
    rejection_reason = serializers.SerializerMethodField()
    line_items = BookingLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id',
            'user',
            'staff',
            'venue',
            'package',
            'description',
            'extra_services',
            'start_datetime',
            'end_datetime',
            'status',
            'advance_paid',
            'total_price',
            'coupon',
            'created_at',
            'rejection_reason',
            'cancellation_reason',
            'line_items',
            'date_changes_count',
            'is_entregado',
            'entregado_after_status',
            'hora_entrega',
        ]

    def get_rejection_reason(self, obj):
        """Get rejection reason from AdminAction if status is 'rechazado'"""
        if obj.status == 'rechazado':
            try:
                from dashboard.models import AdminAction
                admin_action = AdminAction.objects.filter(
                    action='booking_rejected',
                    target_id=str(obj.id)
                ).order_by('-created_at').first()
                
                if admin_action:
                    # Extract the reason from the description
                    description = admin_action.description
                    if 'Reason:' in description:
                        reason = description.split('Reason: ')[-1]
                        return reason
                    return description
                return None
            except Exception:
                return None
        return None

    def create(self, validated_data):
        venue_data = validated_data.pop('venue')
        package_data = validated_data.pop('package')
        extra_services_data = validated_data.pop('extra_services', [])

        venue = Venue.objects.get(id=venue_data['id'])
        package = Package.objects.get(id=package_data['id'])

        # Check if the time range is available (overlap detection, handles after-midnight)
        start_datetime = validated_data.get('start_datetime')
        end_datetime = validated_data.get('end_datetime')

        if start_datetime and end_datetime:
            if not Booking.is_date_available(venue=venue, start_datetime=start_datetime, end_datetime=end_datetime):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'start_datetime': 'This time range is not available for the selected venue.',
                    'end_datetime': 'This time range is not available for the selected venue.',
                })

        booking = Booking.objects.create(venue=venue, package=package, **validated_data)

        for service_data in extra_services_data:
            service = ExtraService.objects.get(id=service_data['id'])
            booking.extra_services.add(service)

        booking.create_line_items()
        booking.total_price = booking.calculate_total()
        booking.save()
        return booking

    def update(self, instance, validated_data):
        composition_changed = False

        if 'venue' in validated_data:
            venue_data = validated_data.pop('venue')
            instance.venue = Venue.objects.get(id=venue_data['id'])

        if 'package' in validated_data:
            package_data = validated_data.pop('package')
            instance.package = Package.objects.get(id=package_data['id'])
            composition_changed = True

        if 'extra_services' in validated_data:
            extra_services_data = validated_data.pop('extra_services')
            instance.extra_services.clear()
            for service_data in extra_services_data:
                service = ExtraService.objects.get(id=service_data['id'])
                instance.extra_services.add(service)
            composition_changed = True

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if composition_changed:
            instance.create_line_items()

        instance.save()
        return instance

class BookingListSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    package_name = serializers.CharField(source='package.title', read_only=True)
    package_price = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    extras_with_prices = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'user',
            'description',
            'status',
            'start_datetime',
            'end_datetime',
            'package_name',
            'package_price',
            'total_price',
            'advance_paid',
            'status_display',
            'extras_with_prices',
            'rejection_reason',
        ]

    def get_rejection_reason(self, obj):
        """Get rejection reason from AdminAction if status is 'rechazado'"""
        if obj.status == 'rechazado':
            try:
                from dashboard.models import AdminAction
                admin_action = AdminAction.objects.filter(
                    action='booking_rejected',
                    target_id=str(obj.id)
                ).order_by('-created_at').first()
                
                if admin_action:
                    # Extract the reason from the description
                    description = admin_action.description
                    if 'Reason:' in description:
                        reason = description.split('Reason:' + ' ')[-1]
                        return reason
                    return description
                return None
            except Exception:
                return None
        return None

    def get_package_price(self, obj):
        line_item = obj.line_items.filter(item_type='package').first()
        if line_item:
            return str(line_item.unit_price)
        return str(obj.package.price) if obj.package else None

    def get_extras_with_prices(self, obj):
        line_items = obj.line_items.filter(item_type='extra_service')
        if line_items.exists():
            return [{'name': item.description, 'price': str(item.unit_price)} for item in line_items]
        # Fallback for legacy bookings without line items
        return [{'name': extra.name, 'price': str(extra.price)} for extra in obj.extra_services.all()]

class BookingCreateSerializer(serializers.ModelSerializer):
    package_id = serializers.IntegerField(write_only=True)
    extra_service_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Booking
        fields = [
            'package_id',
            'extra_service_ids',
            'start_datetime',
            'end_datetime',
            'description',
            'status',
        ]

    def create(self, validated_data):
        package_id = validated_data.pop('package_id')
        extra_service_ids = validated_data.pop('extra_service_ids', [])

        from rest_framework.exceptions import ValidationError
        from django.utils import timezone as tz

        # Always apply configured open/close hours on create.
        # Staff can override times by editing the booking after creation (PATCH/PUT).
        config = VenueConfiguration.get_config()

        def apply_time(datetime_val, time_val):
            if datetime_val is None:
                return datetime_val
            if tz.is_aware(datetime_val):
                local_dt = tz.localtime(datetime_val)
                combined = dt_module.datetime.combine(local_dt.date(), time_val)
                return tz.make_aware(combined)
            return dt_module.datetime.combine(datetime_val.date(), time_val)

        if 'start_datetime' in validated_data:
            validated_data['start_datetime'] = apply_time(validated_data['start_datetime'], config.open_time)
        if 'end_datetime' in validated_data:
            validated_data['end_datetime'] = apply_time(validated_data['end_datetime'], config.close_time)

        # Get venue - allow venue_id in request or use default
        venue_id = self.context.get('venue_id', 1)
        try:
            venue = Venue.objects.get(id=venue_id)
        except Venue.DoesNotExist:
            raise ValidationError({'venue': f'Venue with id {venue_id} does not exist.'})
        try:
            package = Package.objects.get(id=package_id)
        except Package.DoesNotExist:
            raise ValidationError({'package_id': 'Package does not exist.'})

        # Validate all extra_service_ids exist
        services = []
        for service_id in extra_service_ids:
            try:
                service = ExtraService.objects.get(id=service_id)
                services.append(service)
            except ExtraService.DoesNotExist:
                raise ValidationError({'extra_service_ids': f'ExtraService with id {service_id} does not exist.'})

        # Remove user from validated_data to avoid conflict
        validated_data.pop('user', None)

        # Set default status if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'solicitud'

        # Get user - use request user or first staff admin
        request_user = self.context['request'].user
        if request_user.is_authenticated:
            user = request_user
        else:
            # Get first staff admin user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.filter(is_staff=True).first()
                if not user:
                    raise ValidationError({'user': 'No staff admin user found.'})
            except Exception:
                raise ValidationError({'user': 'Error finding staff admin user.'})

        booking = Booking.objects.create(
            venue=venue,
            package=package,
            user=user,
            **validated_data
        )

        for service in services:
            booking.extra_services.add(service)

        booking.create_line_items()
        booking.total_price = booking.calculate_total()
        booking.save()
        return booking

class BookingUpdateSerializer(serializers.ModelSerializer):
    package_id = serializers.IntegerField(write_only=True, required=False)
    extra_service_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Booking
        fields = [
            'package_id',
            'extra_service_ids',
            'start_datetime',
            'end_datetime',
            'status',
            'cancellation_reason',
            'hora_entrega',
        ]

    def update(self, instance, validated_data):
        from rest_framework.exceptions import ValidationError
        from django.utils import timezone

        composition_changed = False
        request = self.context.get('request')
        is_staff = request and request.user.is_staff

        # Enforce date change rules for non-staff users
        new_start = validated_data.get('start_datetime')
        if not is_staff and new_start is not None and new_start != instance.start_datetime:
            if instance.date_changes_count >= 1:
                raise ValidationError({
                    'start_datetime': 'Solo se permite un cambio de fecha por evento.'
                })
            days_until_event = (instance.start_datetime.date() - timezone.now().date()).days
            if days_until_event < 21:
                raise ValidationError({
                    'start_datetime': 'Los cambios de fecha deben solicitarse con al menos 3 semanas de anticipación.'
                })
            validated_data['date_changes_count'] = instance.date_changes_count + 1

        # Handle package update
        if 'package_id' in validated_data:
            package_id = validated_data.pop('package_id')
            try:
                instance.package = Package.objects.get(id=package_id)
                composition_changed = True
            except Package.DoesNotExist:
                raise ValidationError({'package_id': 'Package does not exist.'})

        # Handle extra services update
        if 'extra_service_ids' in validated_data:
            extra_service_ids = validated_data.pop('extra_service_ids')
            instance.extra_services.clear()
            for service_id in extra_service_ids:
                try:
                    service = ExtraService.objects.get(id=service_id)
                    instance.extra_services.add(service)
                except ExtraService.DoesNotExist:
                    raise ValidationError({'extra_service_ids': f'ExtraService with id {service_id} does not exist.'})
            composition_changed = True

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if composition_changed:
            instance.create_line_items()

        instance.save()
        return instance

class BookingWishSerializer(serializers.ModelSerializer):
    #venue = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.all(), required=False, allow_null=True)

    class Meta:
        model = BookingWish
        fields = ['id', 'wished_start_datetime']

    def create(self, validated_data):
        if 'venue' not in validated_data or validated_data['venue'] is None:
            from .models import Venue
            validated_data['venue'] = Venue.objects.get(id=1)
        return super().create(validated_data)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'created_at', 'read', 'booking', 'type']
        read_only_fields = ['id', 'user', 'created_at', 'booking', 'type']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'booking', 'user', 'rating', 'review', 'created_at', 'updated_at']
        read_only_fields = ['booking', 'user', 'created_at', 'updated_at']