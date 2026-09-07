"""The WB2 integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_MAC, CONF_TYPE, DEVICE_TYPE_LIGHT, DEVICE_TYPE_RADAR, DEVICE_TYPE_SWITCH, DOMAIN
from .coordinator import Wb2Coordinator
from .tcp_client import Wb2Client

_LOGGER = logging.getLogger(__name__)


def _platforms_for(entry: ConfigEntry) -> list[str]:
    """Return the platform domains this device type should load."""
    if entry.data.get(CONF_TYPE) == DEVICE_TYPE_SWITCH:
        return [SWITCH_DOMAIN]
    if entry.data.get(CONF_TYPE) == DEVICE_TYPE_RADAR:
        return [BINARY_SENSOR_DOMAIN, SENSOR_DOMAIN, BUTTON_DOMAIN]
    return [LIGHT_DOMAIN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WB2 from a config entry."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    host_ip: str | None = entry.data.get("host_ip")

    client = Wb2Client(host, port, host_ip=host_ip)
    coordinator = Wb2Coordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Check if device supports push reporting
    state = coordinator.data
    if state and getattr(state, "push", None):
        from .push_server import PushServer

        push_server = PushServer.get_instance(hass)
        await push_server.async_start()
        mac = entry.data.get(CONF_MAC)
        if mac:
            push_server.register(mac, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, _platforms_for(entry))
    entry.async_on_unload(coordinator.async_shutdown)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, _platforms_for(entry)
    )

    coordinator: Wb2Coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.client.close()

    # Unregister from push server
    mac = entry.data.get(CONF_MAC)
    if mac:
        from .push_server import PushServer

        push_server = PushServer.get_instance(hass)
        push_server.unregister(mac)

    return unload_ok
