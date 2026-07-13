from django.conf import settings
from django.db import models
import datetime
from django.dispatch import receiver
from django.db.models.signals import post_save
from shortuuid.django_fields import ShortUUIDField
import uuid
from django.utils.text import slugify
from users.models import UserAccount, Profile
from decimal import Decimal


ICON_TYPE= (
    ("Bootstrap Icons", "Bootstrap Icons"),
    ("Fontawesome Icons", "Fontawesome Icons"),
    ("Box Icons", "Box Icons"),
    ("Remi Icons", "Remi Icons"),
    ("Flat Icons", "Flat Icons")
)


class VenueConfiguration(models.Model):
    open_time = models.TimeField(default=datetime.time(10, 0))
    close_time = models.TimeField(default=datetime.time(22, 0))

    class Meta:
        verbose_name = "Configuración del Venue"
        verbose_name_plural = "Configuración del Venue"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.open_time == self.close_time:
            raise ValidationError("El horario de apertura y cierre no pueden ser iguales.")

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'open_time': datetime.time(10, 0),
            'close_time': datetime.time(22, 0),
        })
        return obj

    def __str__(self):
        return f"Horario: {self.open_time.strftime('%H:%M')} - {self.close_time.strftime('%H:%M')}"


class Package(models.Model):
    n_people = models.IntegerField(default=30)
    price = models.FloatField()
    title = models.CharField(max_length = 255, blank = True)
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    class Meta:
       ordering = ('n_people',)
    def __str__(self):
        return self.title + " de " + str(self.n_people) + " personas"

class ExtraService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    def __str__(self):
        return self.name


class Rule(models.Model):
    title = models.CharField(max_length = 255)
    desciption = models.CharField(max_length = 255) 
    
    def __str__(self):
        return self.title

class Venue(models.Model):
    name = models.CharField(max_length = 255, blank = True)
    address = models.CharField(max_length = 255, blank = True)
    active = models.BooleanField(default=True)
    slug = models.SlugField(unique = True, default="")
    
    def __str__(self):
        return self.name
    
    def __save__(self, *args, **kwargs):
        if self.slug == "" or self.slug is None:
            self.slug = slugify(self.name)
        
        super(Venue, self).save(*args, **kwargs)






class Coupon(models.Model):
    DISCOUNT_TYPES = [('percent', 'Porcentaje'), ('fixed', 'Fijo')]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='percent')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.PositiveIntegerField()
    current_uses = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_until = models.DateField(null=True, blank=True)

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active or self.current_uses >= self.max_uses:
            return False
        if self.valid_until and self.valid_until < timezone.now().date():
            return False
        return True

    def get_discount_amount(self, subtotal):
        subtotal = Decimal(str(subtotal))
        if self.discount_type == 'fixed':
            return min(Decimal(str(self.discount_amount or 0)), subtotal)
        pct = Decimal(str(self.discount_percent or 0))
        return (subtotal * pct / Decimal('100')).quantize(Decimal('0.01'))

    def label(self):
        if self.discount_type == 'fixed':
            return f'{self.code} (-${self.discount_amount})'
        return f'{self.code} (-{self.discount_percent}%)'


class Booking(models.Model):
    STATUS_CHOICES = (
        ("solicitud", "Solicitud de Reserva"),
        ("aceptacion", "Aceptación de Reserva"),
        ("apartado", "Apartado inicial"),
        ("liquidado", "Monto liquidado"),
        ("liquidado_entregado", "Monto liquidado y lugar entregado"),
        ("entregado", "Entregado"),
        ("finalizado", "Reserva finalizada"),
        ("cancelado", "Reserva cancelada"),
        ("rechazado", "Rechazado"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="bookings", on_delete=models.CASCADE)
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="managed_bookings", on_delete=models.SET_NULL, null=True, blank=True)
    venue = models.ForeignKey(Venue, related_name="bookings", on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    extra_services = models.ManyToManyField(ExtraService, blank=True)
    description = models.TextField(blank=True, null=True)
    start_datetime = models.DateTimeField()
    start_date = models.DateField(editable=False, db_index=True, null=True)
    end_datetime = models.DateTimeField()
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='solicitud')
    is_entregado = models.BooleanField(default=False)
    entregado_after_status = models.CharField(max_length=20, null=True, blank=True)
    hora_entrega = models.TimeField(null=True, blank=True)
    visible_to_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="visible_bookings", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    date_changes_count = models.IntegerField(default=0)
    cancellation_reason = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["start_datetime", "end_datetime"]),
        ]
        ordering = ['start_datetime']
        # Note: Removed the unique constraint as it was too restrictive
        # Now we handle date conflicts in the save method and validation
  # Calculate total price — uses locked line items when available, falls back to live prices
    def calculate_total(self):
        if self.pk:
            line_items = self.line_items.all()
            if line_items.exists():
                total = sum(item.unit_price * item.quantity for item in line_items)
                return total.quantize(Decimal('0.01'))

        # Fallback: live prices (first save, or legacy bookings without line items)
        total = Decimal('0.00')
        package = getattr(self, 'package', None)
        if package is not None:
            total = Decimal(str(package.price))
        try:
            if hasattr(self, 'extra_services') and self.pk:
                for extra in self.extra_services.all():
                    total += extra.price
        except Exception:
            pass
        coupon = getattr(self, 'coupon', None)
        if coupon is not None and hasattr(coupon, 'is_valid') and coupon.is_valid():
            total -= coupon.get_discount_amount(total)
        return total.quantize(Decimal('0.01'))

    def create_line_items(self):
        """Snapshot current package, extra services, and coupon into immutable line items."""
        self.line_items.all().delete()
        items = []
        if self.package:
            items.append(BookingLineItem(
                booking=self,
                item_type='package',
                description=str(self.package),
                unit_price=Decimal(str(self.package.price)),
            ))
        for extra in self.extra_services.all():
            items.append(BookingLineItem(
                booking=self,
                item_type='extra_service',
                description=extra.name,
                unit_price=extra.price,
            ))
        coupon = getattr(self, 'coupon', None)
        if coupon and coupon.is_valid():
            subtotal = sum(i.unit_price for i in items)
            discount_amount = coupon.get_discount_amount(subtotal)
            items.append(BookingLineItem(
                booking=self,
                item_type='discount',
                description=f'Cupón {coupon.label()}',
                unit_price=-discount_amount,
            ))
        BookingLineItem.objects.bulk_create(items)

    # Override save to set total_price and slug correctly
    def save(self, *args, **kwargs):
        self.total_price = self.calculate_total()
        # Set start_date from start_datetime
        if self.start_datetime:
            self.start_date = self.start_datetime.date()
        # Create slug if missing
        if not self.slug:
            self.slug = self._generate_unique_slug()
        
        # Update status logic based on advance payment
        if self.advance_paid:
            if self.advance_paid > 0 and self.status == "aceptacion":
                self.status = "apartado"
            if self.advance_paid >= self.total_price and  self.status not in ["liquidado","entregado", "finalizado","cancelado","rechazado"]:
                self.status = "liquidado"
        
        # Validate the booking before saving (only if we have required fields)
        if self.venue and self.start_datetime:
            self.clean()
            
        super().save(*args, **kwargs)


    STATUS_CHOICES = (
        ("solicitud", "Solicitud de Reserva"),
        ("aceptacion", "Aceptación de Reserva"),
        ("apartado", "Apartado inicial"),
        ("liquidado", "Monto liquidado"),
        ("liquidado_entregado", "Monto liquidado y lugar entregado"),
        ("entregado", "Entregado"),
        ("finalizado", "Reserva finalizada"),
        ("cancelado", "Reserva cancelada"),
        ("rechazado", "Rechazado"),
    )
    # String representation - use client full name and start date/time
    def __str__(self):
        user = getattr(self, 'user', None)
        dt = getattr(self, 'start_datetime', None)
        if user is not None and hasattr(user, 'first_name') and hasattr(user, 'last_name'):
            user_name = f"{user.first_name} {user.last_name}"
        else:
            user_name = "Unknown user"
        date_str = dt.strftime('%Y-%m-%d %H:%M') if dt else "No date"
        return f"Booking by {user_name} on {date_str}"

    # Property for average rating (assuming related Review model)
    @property
    def event_rating(self):
        reviews = getattr(self, 'review_set', None)
        if reviews is not None:
            all_reviews = reviews.all()
            if all_reviews.exists():
                return all_reviews.first().rating
        return None

    # Property for event review text
    @property
    def event_review(self):
        reviews = getattr(self, 'review_set', None)
        if reviews is not None:
            all_reviews = reviews.all()
            if all_reviews.exists():
                return all_reviews.first().review
        return None

    @classmethod
    def is_date_available(cls, venue, start_datetime, end_datetime, exclude_booking_id=None):
        """
        Check if a time range is available for a venue using overlap detection.
        Handles bookings that go past midnight correctly.
        """
        active_statuses = ['solicitud', 'aceptacion', 'apartado', 'liquidado', 'liquidado_entregado', 'entregado']

        conflicting_bookings = cls.objects.filter(
            venue=venue,
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime,
            status__in=active_statuses,
        ).exclude(id=exclude_booking_id)

        return not conflicting_bookings.exists()

    @classmethod
    def get_available_dates(cls, venue, start_date=None, end_date=None, days_ahead=30):
        """
        Get available dates for a specific venue using time-overlap detection.
        A date is unavailable if any booking's time range overlaps with any part of that day.
        Handles bookings that run past midnight correctly.
        """
        from django.utils import timezone
        import datetime

        if not start_date:
            start_date = timezone.now().date()
        if not end_date:
            end_date = start_date + datetime.timedelta(days=days_ahead)

        active_statuses = ['solicitud', 'aceptacion', 'apartado', 'liquidado', 'liquidado_entregado', 'entregado']

        use_tz = timezone.is_aware(timezone.now())

        def make_dt(d, t=datetime.time.min):
            combined = datetime.datetime.combine(d, t)
            return timezone.make_aware(combined) if use_tz else combined

        # Fetch all bookings that could overlap with any day in range
        range_start = make_dt(start_date)
        range_end = make_dt(end_date + datetime.timedelta(days=1))

        bookings = list(cls.objects.filter(
            venue=venue,
            status__in=active_statuses,
            start_datetime__lt=range_end,
            end_datetime__gt=range_start,
        ).values_list('start_datetime', 'end_datetime'))

        available_dates = []
        current_date = start_date
        while current_date <= end_date:
            day_start = make_dt(current_date)
            day_end = make_dt(current_date + datetime.timedelta(days=1))
            is_booked = any(b_start < day_end and b_end > day_start for b_start, b_end in bookings)
            if not is_booked:
                available_dates.append(current_date)
            current_date += datetime.timedelta(days=1)

        return available_dates

    def _generate_unique_slug(self):
        """Generate a unique slug for the booking"""
        import uuid
        
        dt = getattr(self, 'start_datetime', None)
        user = getattr(self, 'user', None)
        
        if dt and user and hasattr(user, 'id'):
            date_str = dt.strftime('%Y%m%d%H%M')
            user_id = user.id
            
            # Try to generate a unique slug
            max_attempts = 10
            for attempt in range(max_attempts):
                unique_suffix = uuid.uuid4().hex[:6]
                slug = slugify(f"{user_id}-{date_str}-{unique_suffix}")
                
                # Check if this slug already exists
                if not Booking.objects.filter(slug=slug).exclude(id=self.pk).exists():
                    return slug
            
            # If we can't find a unique slug after max attempts, use a completely random one
            return slugify(f"booking-{uuid.uuid4().hex[:12]}")
        else:
            # Fallback slug generation
            return slugify(f"booking-{uuid.uuid4().hex[:12]}")

    @classmethod
    def fix_duplicate_slugs(cls):
        """Fix any existing duplicate slugs in the database"""
        from django.db.models import Count
        
        # Find duplicate slugs
        duplicate_slugs = cls.objects.values('slug').annotate(
            count=Count('slug')
        ).filter(count__gt=1)
        
        for duplicate in duplicate_slugs:
            slug = duplicate['slug']
            bookings = cls.objects.filter(slug=slug).order_by('created_at')
            
            # Keep the first booking with the original slug, update others
            for i, booking in enumerate(bookings[1:], 1):
                new_slug = f"{slug}-{i}"
                # Ensure the new slug is unique
                counter = 1
                while cls.objects.filter(slug=new_slug).exists():
                    new_slug = f"{slug}-{counter}"
                    counter += 1
                booking.slug = new_slug
                booking.save(update_fields=['slug'])

    def clean(self):
        """Validate the booking before saving"""
        from django.core.exceptions import ValidationError
        
        # Check if this is a new booking or status is being changed to active
        if self.pk is None or self.status in ['solicitud', 'aceptacion', 'apartado', 'liquidado', 'liquidado_entregado', 'entregado']:
            if self.venue and self.start_datetime and self.end_datetime:
                is_available = self.is_date_available(
                    self.venue,
                    self.start_datetime,
                    self.end_datetime,
                    exclude_booking_id=self.pk,
                )
                if not is_available:
                    raise ValidationError({
                        'start_datetime': 'This time range is not available for the selected venue.',
                        'end_datetime': 'This time range is not available for the selected venue.',
                    })
        
        super().clean()
    
    
class VenueFeatures(models.Model):
    hotel = models.ForeignKey(Venue, on_delete=models.CASCADE)
    icon_type = models.CharField(max_length=100, null=True, blank=True, choices=ICON_TYPE)
    icon = models.CharField(max_length=100, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.name)


class BookingWish(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    venue = models.ForeignKey('Venue', on_delete=models.CASCADE)
    wished_start_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'venue', 'wished_start_datetime')

    def __str__(self):
        return f"{self.user} esta en espera en {self.venue} para {self.wished_start_datetime}  "


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    booking = models.ForeignKey('Booking', null=True, blank=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, default='general')

    def __str__(self):
        return f"Notification for {self.user}: {self.message[:30]}"


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey('Booking', related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='booking_reviews', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('booking', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review {self.rating}/5 by {self.user} for Booking {self.booking_id}"


class BookingLineItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('package', 'Package'),
        ('extra_service', 'Extra Service'),
        ('discount', 'Discount'),
    ]

    booking = models.ForeignKey(Booking, related_name='line_items', on_delete=models.CASCADE)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.description}: ${self.unit_price}"
