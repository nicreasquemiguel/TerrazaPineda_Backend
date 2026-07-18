from django.db import models

from booking.models import Venue


class SmartDevice(models.Model):
    venue = models.ForeignKey(Venue, related_name='smart_devices', on_delete=models.CASCADE)
    tuya_device_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=100)
    supports_color = models.BooleanField(default=False)
    power_dp_code = models.CharField(
        max_length=40, default='switch_led',
        help_text="Tuya DP code for on/off, confirmed per device via Tuya's Device Debugging panel (e.g. switch_led, switch_1).",
    )
    color_dp_code = models.CharField(max_length=40, default='colour_data_v2')
    color_value_scale = models.PositiveIntegerField(
        default=100,
        help_text="Max value for the s/v components of colour_data_v2 on this device (100 or 1000, varies by model).",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['venue', 'order', 'name']

    def __str__(self):
        return f"{self.name} ({self.venue.name})"
