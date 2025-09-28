from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from booking.models import Booking
from django.db.models import Sum


@receiver(post_save, sender=Payment)
def update_booking_status_on_payment(sender, instance, created, **kwargs):
    if created and instance.status == "paid":
        booking = instance.order.booking

        advance_payment_amount = getattr(booking, "advance_payment_amount", 0)
        total_amount = booking.total_price

        # Sum all paid payments for this booking’s orders
        paid_payments_sum = Payment.objects.filter(
            order__booking=booking,
            status="paid"
        ).aggregate(total_paid=Sum("amount"))["total_paid"] or 0

        # Check and update status based on sums and current booking status
        if booking.status == "aceptacion":
            if paid_payments_sum >= advance_payment_amount and advance_payment_amount > 0:
                booking.status = "apartado"
                booking.save()
            elif advance_payment_amount == 0 and paid_payments_sum >= total_amount:
                booking.status = "liquidado"
                booking.save()

        elif booking.status == "apartado":
            remaining = total_amount - advance_payment_amount
            if paid_payments_sum >= total_amount:
                booking.status = "liquidado"
                booking.save()


@receiver(post_save, sender=Payment)
def update_booking_advance_paid(sender, instance, created, **kwargs):
    """Automatically update booking advance_paid when a payment is created"""
    if created and instance.status == 'paid':
        booking = instance.order.booking
        # Sum all paid payments for this booking
        total_paid = sum(
            payment.amount 
            for payment in instance.order.payments.filter(status='paid')
        )
        booking.advance_paid = total_paid
        booking.save()
        
        # Check if booking is fully paid and update order status
        if booking.advance_paid >= booking.total_price:
            instance.order.status = "paid"
            instance.order.save()