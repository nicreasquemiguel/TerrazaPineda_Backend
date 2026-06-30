from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Booking, Notification

try:
    from users.email_service import TerrazaEmailService
except ImportError:
    TerrazaEmailService = None

try:
    from . import google_calendar as gcal
except ImportError:
    gcal = None

@receiver(pre_save, sender=Booking)
def booking_status_change_notification(sender, instance, **kwargs):
    if not instance.pk:
        return  # New booking, not an update
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    # Status change
    if old.status != instance.status:
        Notification.objects.create(
            user=instance.user,
            message=f"El estatus de tu evento cambio a {instance.get_status_display()}",
            booking=instance,
            type='status_change'
        )
        
        # Send email notification
        if TerrazaEmailService:
            try:
                TerrazaEmailService.send_booking_status_update(
                    user=instance.user,
                    booking=instance,
                    old_status=old.get_status_display()
                )
            except Exception as e:
                print(f"Error sending booking status update email: {e}")
    # Paid change (assuming a boolean 'paid' field or similar)
    if hasattr(instance, 'paid') and getattr(old, 'paid', None) != getattr(instance, 'paid', None):
        if getattr(instance, 'paid', False):
            Notification.objects.create(
                user=instance.user,
                message="Tú reserva ah sido pagada en su totalidad, gracias.",
                booking=instance,
                type='payment'
            )
    # Cancellation
    if instance.status == 'cancelled' and old.status != 'cancelled':
        Notification.objects.create(
            user=instance.user,
            message="Tú evento ah sido cancelado, lo lamentamos.",
            booking=instance,
            type='cancelled'
        )

@receiver(post_save, sender=Booking)
def booking_created_notification(sender, instance, created, **kwargs):
    """Send confirmation email when a new booking is created."""
    if created and TerrazaEmailService:
        try:
            TerrazaEmailService.send_booking_confirmation(
                user=instance.user,
                booking=instance
            )
        except Exception as e:
            print(f"Error sending booking confirmation email: {e}")


@receiver(post_save, sender=Booking)
def sync_booking_to_google_calendar(sender, instance, created, **kwargs):
    """Create or update a Google Calendar event whenever a booking is saved."""
    if not gcal:
        return

    if created:
        event_id = gcal.create_event(instance)
        if event_id:
            # Use update_fields to avoid triggering signals recursively
            Booking.objects.filter(pk=instance.pk).update(google_calendar_event_id=event_id)
            instance.google_calendar_event_id = event_id
    else:
        if instance.google_calendar_event_id:
            gcal.update_event(instance, instance.google_calendar_event_id)
        else:
            # No event ID yet — create it now
            event_id = gcal.create_event(instance)
            if event_id:
                Booking.objects.filter(pk=instance.pk).update(google_calendar_event_id=event_id)
                instance.google_calendar_event_id = event_id