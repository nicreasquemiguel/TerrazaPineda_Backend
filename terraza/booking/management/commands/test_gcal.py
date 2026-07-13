"""
Verify the live Google Calendar API connection (service account auth).

Usage:
    python manage.py test_gcal
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from booking.google_calendar import GOOGLE_AVAILABLE, _get_service


class Command(BaseCommand):
    help = "Check whether the Google Calendar service account connection is working"

    def handle(self, *args, **options):
        self.stdout.write(f"google-api-python-client installed: {GOOGLE_AVAILABLE}")

        has_json = bool(getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON', None))
        has_file = bool(getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_KEY_FILE', None))
        calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary')

        self.stdout.write(f"GOOGLE_SERVICE_ACCOUNT_JSON set: {has_json}")
        self.stdout.write(f"GOOGLE_SERVICE_ACCOUNT_KEY_FILE set: {has_file}")
        self.stdout.write(f"GOOGLE_CALENDAR_ID: {calendar_id}")

        if not GOOGLE_AVAILABLE:
            self.stdout.write(self.style.ERROR(
                "\ngoogle-api-python-client / google-auth are not installed."
            ))
            return

        if not has_json and not has_file:
            self.stdout.write(self.style.ERROR(
                "\nNo credentials configured — set GOOGLE_SERVICE_ACCOUNT_JSON "
                "or GOOGLE_SERVICE_ACCOUNT_KEY_FILE (in .env or the environment)."
            ))
            return

        service = _get_service()
        if not service:
            self.stdout.write(self.style.ERROR(
                "\nCredentials are set but service build failed — check the "
                "server logs above for the '[Google Calendar] Failed to build "
                "service' error."
            ))
            return

        try:
            cal = service.calendars().get(calendarId=calendar_id).execute()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nAPI call failed: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\nConnected. Calendar: \"{cal.get('summary')}\" "
            f"(timeZone: {cal.get('timeZone')})"
        ))
