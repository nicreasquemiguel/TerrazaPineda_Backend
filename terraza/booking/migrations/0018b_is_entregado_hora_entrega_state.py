from django.db import migrations, models


class Migration(migrations.Migration):
    """
    is_entregado and hora_entrega were added directly to the DB before this migration
    was generated. This migration records the state change without touching the DB.
    """

    dependencies = [
        ('booking', '0018_add_venueconfiguration_remove_package_hours'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='booking',
                    name='is_entregado',
                    field=models.BooleanField(default=False),
                ),
                migrations.AddField(
                    model_name='booking',
                    name='hora_entrega',
                    field=models.TimeField(blank=True, null=True),
                ),
            ],
        ),
    ]
