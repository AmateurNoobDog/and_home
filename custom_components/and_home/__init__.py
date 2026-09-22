"""The AND Home integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_MAC, DOMAIN
from .coordinator import Wb2Coordinator
from .tcp_client import Wb2Client

_LOGGER = logging.getLogger(__name__)

_PLATFORM_MAP = {
    "light": [Platform.LIGHT],
    "switch": [Platform.SWITCH],
    "binary_sensor": [Platform.BINARY_SENSOR],
    "button": [Platform.BUTTON],
    "event": [Platform.EVENT],
    "sensor": [Platform.SENSOR],
    "notify": [Platform.NOTIFY],
    "number": [Platform.NUMBER],
}


def _platforms_for_entity_types(entity_types: set[str]) -> list[str]:
    """Derive HA platform domains from entity type set."""
    platforms: set[str] = set()
    for etype in entity_types:
        for platform in _PLATFORM_MAP.get(etype, []):
            platforms.add(platform)
    return list(platforms)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AND Home from a config entry."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    host_ip: str | None = entry.data.get("host_ip")

    client = Wb2Client(host, port, host_ip=host_ip)

    # Discover device info and entity definitions
    try:
        device_info = await client.get_device()
    except Exception:
        _LOGGER.warning("get_device failed for %s, using fallback", host)
        from .tcp_client import Wb2DeviceInfo
        device_info = Wb2DeviceInfo(mac=entry.data.get(CONF_MAC, ""))

    coordinator = Wb2Coordinator(hass, client, device_info)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Derive platforms from entity definitions
    entity_types = {e.type for e in device_info.entities}
    platforms = _platforms_for_entity_types(entity_types)

    if platforms:
        await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Register push server
    from .push_server import PushServer

    push_server = PushServer.get_instance(hass)
    await push_server.async_start()
    push_server.register(entry)

    entry.async_on_unload(coordinator.async_shutdown)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: Wb2Coordinator = hass.data[DOMAIN].pop(entry.entry_id)

    entity_types = {e.type for e in coordinator.device_info.entities}
    platforms = _platforms_for_entity_types(entity_types)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    from .push_server import PushServer
    push_server = PushServer.get_instance(hass)
    push_server.unregister(entry)

    if not push_server._ip_map:
        await push_server.async_stop()

    return unload_ok
