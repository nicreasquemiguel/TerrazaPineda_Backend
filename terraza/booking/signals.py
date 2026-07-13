from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Booking, BookingWish, Notification

try:
    from users.email_service import TerrazaEmailService
except ImportError:
    TerrazaEmailService = None

try:
    from . import google_calendar as gcal
except ImportError:
    gcal = None

User = get_user_model()


@receiver(pre_save, sender=Booking)
def booking_status_change_notification(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.status == instance.status:
        return

    # Notify user of status change
    Notification.objects.create(
        user=instance.user,
        message=f"El estatus de tu evento cambió a {instance.get_status_display()}.",
        booking=instance,
        type='status_change'
    )

    if TerrazaEmailService:
        try:
            TerrazaEmailService.send_booking_status_update(
                user=instance.user,
                booking=instance,
                old_status=old.get_status_display()
            )
        except Exception as e:
            print(f"Error sending booking status update email: {e}")

    # When a booking is cancelled or rejected, notify waitlisted users
    if instance.status in ('cancelado', 'rechazado'):
        _notify_booking_wish_users(instance)


def _notify_booking_wish_users(booking):
    """Notify waitlisted users when a slot opens up on the cancelled booking's date."""
    wishes = BookingWish.objects.filter(
        venue=booking.venue,
        wished_start_datetime__date=booking.start_datetime.date(),
        notified=False,
    ).select_related('user')

    for wish in wishes:
        date_str = booking.start_datetime.strftime('%d/%m/%Y')
        Notification.objects.create(
            user=wish.user,
            message=(
                f"¡Buenas noticias! El {date_str} en {booking.venue.name} "
                f"está disponible nuevamente. ¡Reserva antes de que se ocupe!"
            ),
            booking=None,
            type='wishlist'
        )
        wish.notified = True
        wish.save(update_fields=['notified'])


@receiver(post_save, sender=Booking)
def booking_created_notification(sender, instance, created, **kwargs):
    """On new booking: confirm to customer via in-app + email, and alert all staff."""
    if not created:
        return

    date_str = instance.start_datetime.strftime('%d/%m/%Y')

    # In-app notification for the customer
    Notification.objects.create(
        user=instance.user,
        message=(
            f"Tu solicitud de reserva para el {date_str} fue recibida. "
            f"Te avisaremos pronto."
        ),
        booking=instance,
        type='booking_created'
    )

    # Confirmation email to customer
    if TerrazaEmailService:
        try:
            TerrazaEmailService.send_booking_confirmation(
                user=instance.user,
                booking=instance
            )
        except Exception as e:
            print(f"Error sending booking confirmation email: {e}")

    # In-app notification for all staff members
    customer_name = instance.user.get_full_name() or instance.user.email
    staff_notifications = [
        Notification(
            user=staff_user,
            message=f"Nueva solicitud de {customer_name} para el {date_str}.",
            booking=instance,
            type='new_booking_staff'
        )
        for staff_user in User.objects.filter(is_staff=True)
    ]
    if staff_notifications:
        Notification.objects.bulk_create(staff_notifications)


@receiver(post_save, sender=Booking)
def sync_booking_to_google_calendar(sender, instance, created, **kwargs):
    """Create or update a Google Calendar event whenever a booking is saved."""
    if not gcal:
        return

    if created:
        event_id = gcal.create_event(instance)
        if event_id:
            Booking.objects.filter(pk=instance.pk).update(google_calendar_event_id=event_id)
            instance.google_calendar_event_id = event_id
    else:
        if instance.google_calendar_event_id:
            gcal.update_event(instance, instance.google_calendar_event_id)
        else:
            event_id = gcal.create_event(instance)
            if event_id:
                Booking.objects.filter(pk=instance.pk).update(google_calendar_event_id=event_id)
                instance.google_calendar_event_id = event_id
