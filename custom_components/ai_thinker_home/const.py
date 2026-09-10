"""Constants for the Ai-Thinker integration."""

DOMAIN = "ai_thinker_home"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_TYPE = "type"

DEFAULT_PORT = 9100
DEFAULT_NAME = "Light"
DEFAULT_TYPE = "light"

DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_RADAR = "radar"
DEVICE_TYPE_EVENT = "event"
DEVICE_TYPE_KEY_SENSOR = "key_sensor"

DEFAULT_MODEL = "Ai-Thinker"
DEFAULT_SWITCH_COUNT = 3

SCAN_TIMEOUT = 0.3
POLL_INTERVAL = 10

MDNS_SERVICE_TYPE = "_aitinker._tcp"

# Radar debug switches (must match firmware app_config.h)
RADAR_GATE_DATA_ENABLE = False  # 门数据开关


def short_mac(mac: str | None) -> str:
    """Return the last 6 hex digits of a MAC address, uppercased."""
    if not mac:
        return ""
    cleaned = mac.replace(":", "").replace("-", "").upper()
    return cleaned[-6:] if len(cleaned) >= 6 else cleaned


def model_to_prefix(model: str | None, dtype: str) -> str:
    """Convert device model to entity ID prefix.

    "RD-01" -> "rd01"
    "Ai-WB2-12F" -> "ai_wb2_12f"
    None -> dtype (fallback)
    """
    if not model:
        return dtype
    return model.lower().replace("-", "_")
