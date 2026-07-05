import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import Booking, VenueConfiguration


class Command(BaseCommand):
    help = "Apply configured open/close hours to all existing bookings that have non-standard times."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        config = VenueConfiguration.get_config()
        open_time = config.open_time
        close_time = config.close_time
        use_tz = timezone.is_aware(timezone.now())

        self.stdout.write(
            f"Config: open={open_time.strftime('%H:%M')}  close={close_time.strftime('%H:%M')}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved.\n"))

        bookings = Booking.objects.all().order_by('start_datetime')
        updated = 0
        skipped = 0

        for booking in bookings:
            start = booking.start_datetime
            end = booking.end_datetime

            if start is None or end is None:
                skipped += 1
                continue

            # Determine local date for start and end
            if use_tz:
                start_local = timezone.localtime(start)
                end_local = timezone.localtime(end)
            else:
                start_local = start
                end_local = end

            new_start = self._combine(start_local.date(), open_time, use_tz)
            new_end = self._combine(end_local.date(), close_time, use_tz)

            if new_start == start and new_end == end:
                skipped += 1
                continue

            self.stdout.write(
                f"Booking {booking.id}  [{booking.start_datetime.date()}]\n"
                f"  start: {self._fmt(start)} → {self._fmt(new_start)}\n"
                f"  end:   {self._fmt(end)} → {self._fmt(new_end)}"
            )

            if not dry_run:
                Booking.objects.filter(pk=booking.pk).update(
                    start_datetime=new_start,
                    end_datetime=new_end,
                )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Updated: {updated}  Already correct / skipped: {skipped}"
            )
        )

    def _combine(self, date, time, use_tz):
        combined = datetime.datetime.combine(date, time)
        return timezone.make_aware(combined) if use_tz else combined

    def _fmt(self, dt):
        return timezone.localtime(dt).strftime('%Y-%m-%d %H:%M') if timezone.is_aware(dt) else dt.strftime('%Y-%m-%d %H:%M')
