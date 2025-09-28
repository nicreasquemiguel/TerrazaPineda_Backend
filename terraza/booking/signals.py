from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Booking, Notification

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