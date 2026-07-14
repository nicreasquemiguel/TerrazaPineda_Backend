from decimal import Decimal

from django.db import migrations

HISTORICAL_MINIMUM_DEPOSIT = Decimal('1000')


def backfill(apps, schema_editor):
    VenueConfiguration = apps.get_model('booking', 'VenueConfiguration')
    Booking = apps.get_model('booking', 'Booking')

    VenueConfiguration.objects.filter(minimum_deposit=0).update(
        minimum_deposit=HISTORICAL_MINIMUM_DEPOSIT
    )
    Booking.objects.filter(minimum_deposit=0).update(
        minimum_deposit=HISTORICAL_MINIMUM_DEPOSIT
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0022_booking_minimum_deposit'),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
