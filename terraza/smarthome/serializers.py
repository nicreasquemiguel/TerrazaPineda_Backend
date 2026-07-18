from rest_framework import serializers

from .models import SmartDevice


class SmartDeviceSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = SmartDevice
        fields = ['id', 'venue', 'venue_name', 'name', 'supports_color', 'order', 'is_active']


class DeviceColorSerializer(serializers.Serializer):
    h = serializers.IntegerField(min_value=0, max_value=360)
    s = serializers.IntegerField(min_value=0, max_value=100)
    v = serializers.IntegerField(min_value=0, max_value=100)


class DeviceCommandSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['on', 'off', 'color'])
    color = DeviceColorSerializer(required=False)

    def validate(self, attrs):
        if attrs['action'] == 'color' and 'color' not in attrs:
            raise serializers.ValidationError({"color": "This field is required when action is 'color'."})
        return attrs
