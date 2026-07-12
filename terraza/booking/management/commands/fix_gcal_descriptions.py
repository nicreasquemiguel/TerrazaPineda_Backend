"""
Re-process an .ics file and update descriptions on already-imported bookings.

Matches existing bookings by start_datetime (within a 1-minute window).
Sets description = "<summary>\n<gcal_description>" (gcal_description only if present).

Usage:
    python manage.py fix_gcal_descriptions path/to/calendar.ics
    python manage.py fix_gcal_descriptions calendar.ics --dry-run
"""

import datetime
import re
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz

from booking.models import Booking
from booking.management.commands.import_gcal import parse_ics

MEXICO_TZ = ZoneInfo("America/Mexico_City")


class Command(BaseCommand):
    help = "Update descriptions on already-imported GCal bookings from a .ics file"

    def add_arguments(self, parser):
        parser.add_argument("ics_file", help="Path to the exported .ics file")
        parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
        parser.add_argument(
            "--open-time", default="10:00",
            help="Venue open time used during original import (default: 10:00)",
        )
        parser.add_argument(
            "--close-time", default="22:00",
            help="Venue close time used during original import (default: 22:00)",
        )

    def handle(self, *args, **options):
        ics_path  = options["ics_file"]
        dry_run   = options["dry_run"]

        try:
            open_time  = datetime.time(*[int(x) for x in options["open_time"].split(":")])
            close_time = datetime.time(*[int(x) for x in options["close_time"].split(":")])
        except Exception:
            raise CommandError("Invalid time format. Use HH:MM.")

        try:
            events = parse_ics(ics_path, open_time, close_time)
        except FileNotFoundError:
            raise CommandError(f"File not found: {ics_path}")
        except Exception as e:
            raise CommandError(f"Error parsing .ics: {e}")

        self.stdout.write(f"\nFound {len(events)} event(s) in {ics_path}\n")
        self.stdout.write("─" * 60)

        updated = skipped = not_found = 0

        for ev in events:
            summary    = ev["summary"]
            gcal_desc  = (ev.get("description") or "").strip()
            start      = ev["start"]

            # Build target description
            parts = [summary]
            if gcal_desc:
                parts.append(gcal_desc)
            new_description = "\n".join(parts)

            # Match by start_datetime within ±1 minute
            window_start = start - datetime.timedelta(minutes=1)
            window_end   = start + datetime.timedelta(minutes=1)
            booking = Booking.objects.filter(
                start_datetime__gte=window_start,
                start_datetime__lte=window_end,
            ).first()

            label = f"{summary}  |  {start.strftime('%d/%m/%Y %H:%M')}"

            if not booking:
                self.stdout.write(self.style.WARNING(f"  NOT FOUND   {label}"))
                not_found += 1
                continue

            if booking.description == new_description:
                self.stdout.write(f"  UNCHANGED   {label}")
                skipped += 1
                continue

            if not dry_run:
                booking.description = new_description
                booking.save(update_fields=["description"])

            self.stdout.write(self.style.SUCCESS(
                f"  {'[DRY] ' if dry_run else ''}UPDATED     {label}"
            ))
            updated += 1

        self.stdout.write("─" * 60)
        self.stdout.write(
            f"\nUpdated: {updated}   Unchanged: {skipped}   Not found: {not_found}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠  Dry run — nothing was saved."))
