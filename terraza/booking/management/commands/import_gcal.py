"""
Import Google Calendar events as placeholder bookings.

Usage:
    python manage.py import_gcal path/to/calendar.ics
    python manage.py import_gcal calendar.ics --dry-run        # preview only
    python manage.py import_gcal calendar.ics --status apartado

How to export from Google Calendar:
    Settings (gear icon) → Settings → Import & Export → Export
    A .zip is downloaded; extract it and find the .ics file inside.
"""

import datetime
import re
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as tz

from booking.models import Booking, Package, Venue

MEXICO_TZ = ZoneInfo("America/Mexico_City")


# ── ICS parser ────────────────────────────────────────────────────────────────

def _unfold(text):
    """RFC 5545: a CRLF followed by whitespace is a line continuation."""
    return re.sub(r"\r?\n[ \t]", "", text)


def _unescape_ics(value):
    """RFC 5545 TEXT unescaping: \\n → newline, \\, → comma, \\\\ → backslash."""
    value = value.replace("\\n", "\n").replace("\\N", "\n")
    value = value.replace("\\,", ",")
    value = value.replace("\\;", ";")
    value = value.replace("\\\\", "\\")
    return value


def _parse_dt(prop_name, value):
    """
    Return an aware datetime from an ICS DTSTART/DTEND line.
    prop_name  e.g. "DTSTART;TZID=America/Mexico_City" or "DTSTART;VALUE=DATE"
    value      e.g. "20250615T100000" or "20250615"
    """
    # All-day event ─ no time info
    if "VALUE=DATE" in prop_name or re.fullmatch(r"\d{8}", value.strip()):
        d = datetime.datetime.strptime(value.strip(), "%Y%m%d").date()
        return d  # return a date object; caller decides start vs end time

    # Extract TZID from parameter
    tzid_match = re.search(r"TZID=([^;:]+)", prop_name)
    tzid = tzid_match.group(1) if tzid_match else None

    value = value.strip()

    # UTC literal
    if value.endswith("Z"):
        dt = datetime.datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        return tz.make_aware(dt, ZoneInfo("UTC"))

    dt = datetime.datetime.strptime(value, "%Y%m%dT%H%M%S")
    zone = ZoneInfo(tzid) if tzid else MEXICO_TZ
    return tz.make_aware(dt, zone)


def parse_ics(path, open_time, close_time):
    """Parse .ics file; return list of {summary, start, end, raw_start_is_date}."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = _unfold(text)
    events = []
    current = None

    for line in text.splitlines():
        if line.strip() == "BEGIN:VEVENT":
            current = {}
            continue
        if line.strip() == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
            continue
        if current is None:
            continue

        if ":" not in line:
            continue
        prop, _, value = line.partition(":")
        prop_upper = prop.upper()

        if prop_upper.startswith("DTSTART"):
            parsed = _parse_dt(prop_upper, value)
            current["_start_raw"] = parsed
            current["_start_is_date"] = isinstance(parsed, datetime.date) and not isinstance(parsed, datetime.datetime)

        elif prop_upper.startswith("DTEND"):
            parsed = _parse_dt(prop_upper, value)
            current["_end_raw"] = parsed
            current["_end_is_date"] = isinstance(parsed, datetime.date) and not isinstance(parsed, datetime.datetime)

        elif prop_upper == "SUMMARY":
            current["summary"] = _unescape_ics(value.strip())

        elif prop_upper == "DESCRIPTION":
            current["description"] = _unescape_ics(value.strip())

    # Always use venue open/close times — GCal times are unreliable notes
    result = []
    for ev in events:
        start_raw = ev.get("_start_raw")
        end_raw   = ev.get("_end_raw")
        if not start_raw:
            continue

        # Get the calendar date (works for both date and datetime)
        if isinstance(start_raw, datetime.datetime):
            start_date = start_raw.date()
        else:
            start_date = start_raw

        # For all-day events DTEND is the exclusive next day — step back one day
        if end_raw:
            if isinstance(end_raw, datetime.datetime):
                end_date = end_raw.date()
            else:
                end_date = end_raw - datetime.timedelta(days=1)
        else:
            end_date = start_date

        start = tz.make_aware(
            datetime.datetime.combine(start_date, open_time), MEXICO_TZ
        )
        end = tz.make_aware(
            datetime.datetime.combine(end_date, close_time), MEXICO_TZ
        )

        # close_time midnight (00:00) means it rolls to next day
        if end <= start:
            end += datetime.timedelta(days=1)

        result.append({
            "summary":     ev.get("summary", "Evento importado"),
            "description": ev.get("description", ""),
            "start":       start,
            "end":         end,
        })

    return result


# ── Command ───────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Import Google Calendar .ics events as placeholder bookings"

    def add_arguments(self, parser):
        parser.add_argument("ics_file", help="Path to the exported .ics file")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview what would be created without writing to the DB",
        )
        parser.add_argument(
            "--status", default="aceptacion",
            help="Booking status for imported events (default: aceptacion)",
        )
        parser.add_argument(
            "--past", action="store_true",
            help="Also import events whose end date is in the past",
        )
        parser.add_argument(
            "--open-time", default="10:00",
            help="Venue open time HH:MM (default: 10:00)",
        )
        parser.add_argument(
            "--close-time", default="22:00",
            help="Venue close time HH:MM (default: 22:00)",
        )

    def handle(self, *args, **options):
        ics_path     = options["ics_file"]
        dry_run      = options["dry_run"]
        status       = options["status"]
        include_past = options["past"]

        try:
            open_time  = datetime.time(*[int(x) for x in options["open_time"].split(":")])
            close_time = datetime.time(*[int(x) for x in options["close_time"].split(":")])
        except Exception:
            raise CommandError("Invalid time format. Use HH:MM, e.g. --open-time 10:00")

        # Suppress post_save signals (email + GCal sync) during bulk import
        from django.db.models.signals import post_save
        try:
            from booking import signals as booking_signals
            post_save.disconnect(booking_signals.booking_created_notification, sender=Booking)
            post_save.disconnect(booking_signals.sync_booking_to_google_calendar, sender=Booking)
        except Exception:
            pass

        # ── resolve required DB objects ───────────────────────────────────────
        User = get_user_model()
        staff_user = User.objects.filter(is_staff=True).first()
        if not staff_user:
            raise CommandError("No staff user found in the database.")

        venue = Venue.objects.first()
        if not venue:
            raise CommandError("No Venue found in the database.")

        package = Package.objects.order_by("price").first()
        if not package:
            raise CommandError("No Package found in the database.")

        # ── parse ─────────────────────────────────────────────────────────────
        try:
            events = parse_ics(ics_path, open_time, close_time)
        except FileNotFoundError:
            raise CommandError(f"File not found: {ics_path}")
        except Exception as e:
            raise CommandError(f"Error parsing .ics file: {e}")

        now = tz.now()
        created = skipped_conflict = skipped_past = 0

        self.stdout.write(f"\nFound {len(events)} event(s) in {ics_path}\n")
        self.stdout.write("─" * 60)

        for ev in events:
            summary  = ev["summary"]
            start    = ev["start"]
            end      = ev["end"]
            is_past  = end < now
            label    = f"{summary}  |  {start.strftime('%d/%m/%Y %H:%M')} → {end.strftime('%d/%m/%Y %H:%M')}"

            # Skip past events unless --past flag is set
            if not include_past and is_past:
                self.stdout.write(self.style.WARNING(f"  PAST     {label}"))
                skipped_past += 1
                continue

            # Skip if a booking already blocks this slot
            if not Booking.is_date_available(venue=venue, start_datetime=start, end_datetime=end):
                self.stdout.write(self.style.ERROR(f"  CONFLICT {label}"))
                skipped_conflict += 1
                continue

            # Past events → finalizado; future events → use --status (default aceptacion)
            resolved_status = "finalizado" if is_past else status

            if not dry_run:
                gcal_desc = ev.get("description", "").strip()
                description_parts = ["[GCal]", summary]
                if gcal_desc:
                    description_parts.append(gcal_desc)
                full_description = "\n".join(description_parts)

                b = Booking.objects.create(
                    user=staff_user,
                    venue=venue,
                    package=package,
                    start_datetime=start,
                    end_datetime=end,
                    description=full_description,
                    status=resolved_status,
                    total_price=0,
                    advance_paid=0,
                )
                b.create_line_items()
                b.total_price = b.calculate_total()
                b.save()

            self.stdout.write(self.style.SUCCESS(
                f"  {'[DRY] ' if dry_run else ''}CREATE [{resolved_status}]   {label}"
            ))
            created += 1

        self.stdout.write("─" * 60)
        self.stdout.write(
            f"\nCreated: {created}   "
            f"Conflicts: {skipped_conflict}   "
            f"Past (skipped): {skipped_past}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠  Dry run — nothing was saved."))
