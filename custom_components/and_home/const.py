"""Constants for the AND integration."""

from __future__ import annotations

DOMAIN = "and_home"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_TYPE = "type"

DEFAULT_PORT = 9100
DEFAULT_NAME = "Light"
DEFAULT_TYPE = "light"

SCAN_TIMEOUT = 0.3
POLL_INTERVAL = 10


def normalize_mac(mac: str | None) -> str:
    """Normalize MAC address to uppercase without separators."""
    if not mac:
        return ""
    return mac.replace(":", "").replace("-", "").upper()


def short_mac(mac: str | None) -> str:
    """Return the last 6 hex digits of a MAC address, uppercased."""
    if not mac:
        return ""
    cleaned = normalize_mac(mac)
    return cleaned[-6:] if len(cleaned) >= 6 else cleaned


def device_info(coordinator) -> dict:
    """Build device_info dict for HA entity registration."""
    info = coordinator.device_info
    mac = info.mac
    return {
        "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, info.name)},
        "name": info.name,
        "manufacturer": "AND",
        "model": info.model,
        "sw_version": info.sw_version,
    }
