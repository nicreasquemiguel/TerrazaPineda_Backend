from django.conf import settings
from tuya_connector import TuyaOpenAPI

from .exceptions import TuyaAPIError

_client = None


def get_client():
    global _client
    if _client is None:
        client = TuyaOpenAPI(
            settings.TUYA_API_ENDPOINT,
            settings.TUYA_ACCESS_ID,
            settings.TUYA_ACCESS_SECRET,
        )
        client.connect()
        _client = client
    return _client


def _send_commands(tuya_device_id, commands):
    try:
        response = get_client().post(
            f"/v1.0/iot-03/devices/{tuya_device_id}/commands",
            {"commands": commands},
        )
    except Exception as exc:
        raise TuyaAPIError(f"Failed to send command to device {tuya_device_id}: {exc}") from exc

    if not response.get("success"):
        raise TuyaAPIError(f"Tuya rejected command for device {tuya_device_id}: {response}")
    return response


def turn_device(device, on):
    return _send_commands(device.tuya_device_id, [{"code": device.power_dp_code, "value": bool(on)}])


def set_device_color(device, h, s, v):
    scale = device.color_value_scale
    color_value = {
        "h": int(h),
        "s": int(round(s * scale / 100)),
        "v": int(round(v * scale / 100)),
    }
    return _send_commands(device.tuya_device_id, [{"code": device.color_dp_code, "value": color_value}])


def get_device_status(device):
    try:
        response = get_client().get(f"/v1.0/iot-03/devices/{device.tuya_device_id}/status")
    except Exception as exc:
        raise TuyaAPIError(f"Failed to fetch status for device {device.tuya_device_id}: {exc}") from exc

    if not response.get("success"):
        raise TuyaAPIError(f"Tuya rejected status request for device {device.tuya_device_id}: {response}")
    return response.get("result", [])
