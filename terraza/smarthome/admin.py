from django.contrib import admin

from .models import SmartDevice


@admin.register(SmartDevice)
class SmartDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue', 'tuya_device_id', 'supports_color', 'is_active', 'order']
    list_filter = ['venue', 'supports_color', 'is_active']
    search_fields = ['name', 'tuya_device_id', 'venue__name']
    ordering = ['venue', 'order']
