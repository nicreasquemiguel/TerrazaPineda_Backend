"""
Delete ALL bookings from the database.

Usage:
    python manage.py clear_bookings
    python manage.py clear_bookings --yes   # skip confirmation prompt
"""

from django.core.management.base import BaseCommand
from booking.models import Booking


class Command(BaseCommand):
    help = "Delete ALL bookings from the database (irreversible)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes", action="store_true",
            help="Skip the confirmation prompt",
        )

    def handle(self, *args, **options):
        count = Booking.objects.count()

        if count == 0:
            self.stdout.write("No bookings found. Nothing to delete.")
            return

        self.stdout.write(self.style.WARNING(
            f"\n⚠  This will permanently delete {count} booking(s) and all related data "
            f"(payments, line items, activity logs, notifications).\n"
        ))

        if not options["yes"]:
            confirm = input('Type "borrar todo" to confirm: ')
            if confirm.strip() != "borrar todo":
                self.stdout.write("Cancelled.")
                return

        Booking.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"✓ Deleted {count} booking(s)."))
