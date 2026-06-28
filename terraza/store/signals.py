from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db.models import Sum
from .models import Payment, PaymentOrder
from booking.models import Booking


def _sync_order_amount_due(booking):
    """Recalculate amount_due on all pending orders when booking.total_price changes."""
    total_paid = Payment.objects.filter(
        order__booking=booking,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    for order in booking.payment_orders.filter(status='pending'):
        remaining = max(0, booking.total_price - total_paid)
        PaymentOrder.objects.filter(pk=order.pk).update(amount_due=remaining)


@receiver(m2m_changed, sender=Booking.extra_services.through)
def sync_orders_on_extras_change(sender, instance, action, **kwargs):
    """Adding/removing extra services bypasses booking.save(), so we recalculate here."""
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if not isinstance(instance, Booking):
        return
    # Recalculate total_price in-place (M2M is already committed at post_* stage)
    new_total = instance.calculate_total()
    Booking.objects.filter(pk=instance.pk).update(total_price=new_total)
    instance.total_price = new_total
    _sync_order_amount_due(instance)


@receiver(post_save, sender=Booking)
def sync_orders_on_booking_save(sender, instance, **kwargs):
    """Sync order amount_due whenever booking.total_price changes (package swap, coupon, etc.)."""
    _sync_order_amount_due(instance)


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
