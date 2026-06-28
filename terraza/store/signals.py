from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import Payment, PaymentOrder
from booking.models import Booking


@receiver(post_save, sender=Payment)
def sync_payment_state(sender, instance, created, **kwargs):
    """
    Keep order.amount_due, order.status, booking.advance_paid, and booking.status
    in sync whenever a payment is marked paid — whether created or updated (e.g. admin approval).
    """
    if instance.status != 'paid':
        return

    order = instance.order
    booking = order.booking

    # Aggregate across ALL orders for this booking so multi-order edge cases are handled
    total_paid = Payment.objects.filter(
        order__booking=booking,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # --- Update booking ---
    booking.advance_paid = total_paid
    advance_amount = getattr(booking, 'advance_payment_amount', 0) or 0

    if total_paid >= booking.total_price:
        booking.status = 'liquidado'
    elif advance_amount > 0 and total_paid >= advance_amount and booking.status == 'aceptacion':
        booking.status = 'apartado'

    booking.save()

    # --- Update order (bypass save() to avoid recalculation loop) ---
    remaining = max(0, booking.total_price - total_paid)
    new_status = 'paid' if remaining <= 0 else order.status
    PaymentOrder.objects.filter(pk=order.pk).update(
        amount_due=remaining,
        status=new_status,
    )
