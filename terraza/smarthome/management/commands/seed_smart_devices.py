from django.core.management.base import BaseCommand, CommandError

from booking.models import Venue
from smarthome.models import SmartDevice

# (name, tuya_device_id, supports_color) — the "Smart Bulb 600hz" devices from the
# linked Tuya app account. Deliberately excludes the W601 switches (Entrada, Bomba,
# Bomba Alberca, Lámpara alberca) and "Alberca switch" — those control a pump/entrance,
# not lighting, and weren't confirmed as in-scope for guest control. Add them here too
# if you want them registered the same way.
DEVICES = [
    ("Smart Bulb 600hz 5", "eb5bf2ceff03b44c22cnr5", True),
    ("Smart Bulb 600hz 29", "ebf6bd83d631797f06talq", True),
    ("Smart Bulb 600hz 31", "eb980e6f10b9bf3b89r6mw", True),
    ("Smart Bulb 600hz 32", "eb313a5ec0306be711kkai", True),
]


class Command(BaseCommand):
    help = "Registers the Tuya smart bulbs as SmartDevice rows for a venue (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--venue", type=str, default=None,
            help="Venue slug to attach devices to. Defaults to the only Venue if there's exactly one.",
        )

    def handle(self, *args, **options):
        venue = self._resolve_venue(options["venue"])

        created, updated = 0, 0
        for order, (name, tuya_device_id, supports_color) in enumerate(DEVICES):
            device, was_created = SmartDevice.objects.update_or_create(
                tuya_device_id=tuya_device_id,
                defaults={
                    "venue": venue,
                    "name": name,
                    "supports_color": supports_color,
                    "order": order,
                },
            )
            created += was_created
            updated += not was_created
            self.stdout.write(f"{'Created' if was_created else 'Updated'}: {device.name} ({device.tuya_device_id})")

        self.stdout.write(self.style.SUCCESS(f"Done. {created} created, {updated} updated, venue={venue.name!r}."))

    def _resolve_venue(self, slug):
        if slug:
            try:
                return Venue.objects.get(slug=slug)
            except Venue.DoesNotExist:
                raise CommandError(f"No venue found with slug={slug!r}.")

        venues = list(Venue.objects.all())
        if len(venues) == 1:
            return venues[0]
        if not venues:
            raise CommandError("No venues exist yet — create one first.")
        options_list = ", ".join(f"{v.slug!r}" for v in venues)
        raise CommandError(f"Multiple venues exist, pass --venue <slug>. Options: {options_list}")
