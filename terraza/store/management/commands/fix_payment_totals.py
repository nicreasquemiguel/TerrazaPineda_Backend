from django.core.management.base import BaseCommand
from django.db.models import Sum
from booking.models import Booking
from store.models import Payment, PaymentOrder


class Command(BaseCommand):
    help = "Recalculate advance_paid on all bookings and amount_due on all pending orders"

    def handle(self, *args, **options):
        bookings = Booking.objects.prefetch_related("payment_orders").all()
        fixed_bookings = 0
        fixed_orders = 0

        for booking in bookings:
            total_paid = Payment.objects.filter(
                order__booking=booking,
                status="paid",
            ).aggregate(total=Sum("amount"))["total"] or 0

            if booking.advance_paid != total_paid:
                old = booking.advance_paid
                Booking.objects.filter(pk=booking.pk).update(advance_paid=total_paid)
                self.stdout.write(
                    f"  Booking {booking.id}: advance_paid {old} → {total_paid}"
                )
                fixed_bookings += 1

            remaining = max(0, booking.total_price - total_paid)
            new_status = "paid" if remaining <= 0 else None

            for order in booking.payment_orders.filter(status="pending"):
                update_kwargs = {"amount_due": remaining}
                if new_status:
                    update_kwargs["status"] = new_status
                PaymentOrder.objects.filter(pk=order.pk).update(**update_kwargs)
                self.stdout.write(
                    f"  Order {order.id}: amount_due → {remaining}"
                )
                fixed_orders += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Fixed {fixed_bookings} bookings, {fixed_orders} orders."
        ))
