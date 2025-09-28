from .models import Booking, ExtraService, Package, Venue, BookingWish, Notification, Review
from users.serializers import UserSerializer
from rest_framework import serializers

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

        # Check if the date is available (one event per day per venue)
        start_datetime = validated_data.get('start_datetime')
        
        if start_datetime and hasattr(start_datetime, 'date'):
            if not Booking.is_date_available(
                venue=venue,
                date=start_datetime.date()
            ):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'start_datetime': 'This date is not available for the selected venue.',
                    'end_datetime': 'This date is not available for the selected venue.'
                })

        booking = Booking.objects.create(venue=venue, package=package, **validated_data)

        for service_data in extra_services_data:
            service = ExtraService.objects.get(id=service_data['id'])
            booking.extra_services.add(service)

        extras_price = sum([s.price for s in booking.extra_services.all()])
        booking.total_price = package.price + extras_price
        booking.save()
        return booking

    def update(self, instance, validated_data):
        if 'venue' in validated_data:
            venue_data = validated_data.pop('venue')
            instance.venue = Venue.objects.get(id=venue_data['id'])

        if 'package' in validated_data:
            package_data = validated_data.pop('package')
            instance.package = Package.objects.get(id=package_data['id'])

        if 'extra_services' in validated_data:
            extra_services_data = validated_data.pop('extra_services')
            instance.extra_services.clear()
            for service_data in extra_services_data:
                service = ExtraService.objects.get(id=service_data['id'])
                instance.extra_services.add(service)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        extras_price = sum([s.price for s in instance.extra_services.all()])
        instance.total_price = instance.package.price + extras_price
        instance.save()
        return instance

class BookingListSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source='package.title', read_only=True)
    package_price = serializers.DecimalField(source='package.price', read_only=True, max_digits=10, decimal_places=2)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    extras_with_prices = serializers.SerializerMethodField()
    rejection_reason = serializers.SerializerMethodField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()

    class Meta:
        model = Booking
        fields = [
            'id',
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

    def get_extras_with_prices(self, obj):
        return [
            {
                'name': extra.name,
                'price': str(extra.price)
            }
            for extra in obj.extra_services.all()
        ]

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
            'advance_paid',
        ]

    def update(self, instance, validated_data):
        from rest_framework.exceptions import ValidationError
        
        # Handle package update
        if 'package_id' in validated_data:
            package_id = validated_data.pop('package_id')
            try:
                package = Package.objects.get(id=package_id)
                instance.package = package
            except Package.DoesNotExist:
                raise ValidationError({'package_id': 'Package does not exist.'})

        # Handle extra services update
        if 'extra_service_ids' in validated_data:
            extra_service_ids = validated_data.pop('extra_service_ids')
            # Clear existing extra services
            instance.extra_services.clear()
            # Add new extra services
            for service_id in extra_service_ids:
                try:
                    service = ExtraService.objects.get(id=service_id)
                    instance.extra_services.add(service)
                except ExtraService.DoesNotExist:
                    raise ValidationError({'extra_service_ids': f'ExtraService with id {service_id} does not exist.'})

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

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