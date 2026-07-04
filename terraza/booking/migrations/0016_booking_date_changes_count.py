from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0015_add_bookinglineitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='date_changes_count',
            field=models.IntegerField(default=0),
        ),
    ]
