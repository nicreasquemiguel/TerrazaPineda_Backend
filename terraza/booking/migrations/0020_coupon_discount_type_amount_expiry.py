from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0019_add_entregado_after_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='discount_type',
            field=models.CharField(
                choices=[('percent', 'Porcentaje'), ('fixed', 'Fijo')],
                default='percent',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='coupon',
            name='discount_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='coupon',
            name='valid_until',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='discount_percent',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
