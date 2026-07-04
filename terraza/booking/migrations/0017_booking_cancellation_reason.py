from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0016_booking_date_changes_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='cancellation_reason',
            field=models.TextField(blank=True, null=True),
        ),
    ]
