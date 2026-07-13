"""
Create a single real booking to verify the Google Calendar sync end-to-end
(signals fire normally: confirmation email, staff notifications, and the
Google Calendar event are all created just like a real customer booking).

Usage:
    python manage.py create_test_booking 2026-07-09
    python manage.py create_test_booking 2026-07-09 --status aceptacion
"""

import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz

from booking.models import Booking, Package, Venue, VenueConfiguration

User = get_user_model()


class Command(BaseCommand):
    help = "Create a real test booking on the given date to verify Google Calendar sync"

    def add_arguments(self, parser):
        parser.add_argument("date", help="Booking date, YYYY-MM-DD")
        parser.add_argument("--status", default="solicitud", choices=[c[0] for c in Booking.STATUS_CHOICES])

    def handle(self, *args, **options):
        try:
            day = datetime.datetime.strptime(options["date"], "%Y-%m-%d").date()
        except ValueError:
            raise CommandError("Invalid date. Use YYYY-MM-DD, e.g. 2026-07-09")

        venue = Venue.objects.first()
        if not venue:
            raise CommandError("No Venue found in the database.")

        package = Package.objects.order_by("price").first()
        if not package:
            raise CommandError("No Package found in the database.")

        staff_user = User.objects.filter(is_staff=True).first()
        if not staff_user:
            raise CommandError("No staff user found in the database.")

        config = VenueConfiguration.objects.first()
        open_time = config.open_time if config else datetime.time(10, 0)
        close_time = config.close_time if config else datetime.time(22, 0)

        start = tz.make_aware(datetime.datetime.combine(day, open_time))
        end = tz.make_aware(datetime.datetime.combine(day, close_time))
        if end <= start:
            end += datetime.timedelta(days=1)

        if not Booking.is_date_available(venue, start, end):
            raise CommandError(
                f"{day} is already occupied by a non-cancelled booking for this venue."
            )

        booking = Booking.objects.create(
            user=staff_user,
            venue=venue,
            package=package,
            start_datetime=start,
            end_datetime=end,
            description="[TEST] Reserva de prueba — verificación de sincronización con Google Calendar",
            status=options["status"],
            total_price=0,
            advance_paid=0,
        )
        booking.create_line_items()
        booking.total_price = booking.calculate_total()
        booking.save()
        booking.refresh_from_db()

        self.stdout.write(self.style.SUCCESS(f"\nBooking created: {booking.id}"))
        self.stdout.write(f"User: {staff_user.email}")
        self.stdout.write(f"Venue: {venue.name}   Package: {package.title}")
        self.stdout.write(f"{start} → {end}")
        self.stdout.write(f"google_calendar_event_id: {booking.google_calendar_event_id}")

        if not booking.google_calendar_event_id:
            self.stdout.write(self.style.ERROR(
                "\nNo Google Calendar event id was set — sync failed. Check the "
                "'[Google Calendar]' error printed above (if any)."
            ))
