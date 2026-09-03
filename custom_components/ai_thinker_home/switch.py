"""Support for the Ai-Thinker WB2 multi-channel relay switch."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_NAME,
    CONF_HOST,
    CONF_MAC,
    CONF_PORT,
    CONF_TYPE,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_SWITCH_COUNT,
    DEFAULT_TYPE,
    DOMAIN,
    short_mac,
)
from .coordinator import Wb2Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WB2 relay switches from a config entry."""
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    base_name: str = entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
    mac: str | None = entry.data.get(CONF_MAC)
    dtype: str = entry.data.get(CONF_TYPE, DEFAULT_TYPE)

    device_name = coordinator.data.name if coordinator.data and coordinator.data.name else base_name
    model = coordinator.data.model if coordinator.data and coordinator.data.model else DEFAULT_MODEL
    names = coordinator.data.names if coordinator.data else None
    count = _channel_count(coordinator)

    async_add_entities(
        Wb2Switch(
            coordinator, device_name, model, names, host, port, mac, dtype, channel
        )
        for channel in range(count)
    )


def _channel_count(coordinator: Wb2Coordinator) -> int:
    """Number of relay channels reported by the device (fallback default)."""
    if coordinator.data and coordinator.data.count:
        return coordinator.data.count
    return DEFAULT_SWITCH_COUNT


class Wb2Switch(CoordinatorEntity[Wb2Coordinator], SwitchEntity):
    """One WB2 relay channel exposed as a Home Assistant switch."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: Wb2Coordinator,
        device_name: str,
        model: str,
        names: list[str] | None,
        host: str,
        port: int,
        mac: str | None,
        dtype: str,
        channel: int,
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        short = short_mac(mac)
        if short:
            self.entity_id = f"switch.{dtype}_{short.lower()}_switch_{channel + 1:03d}"
            self._attr_unique_id = f"{DOMAIN}_{mac}_switch_{channel}"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_switch_{channel}"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        if names and channel < len(names) and names[channel]:
            self._attr_name = names[channel]
        else:
            self._attr_name = device_name

        self._attr_device_info = {
            "identifiers": identifiers,
            "name": device_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": "0.6.0",
        }

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data
        if state is None:
            return None
        on = state.channel_state(self._channel)
        if on is None:
            return None
        return bool(on)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available

    async def async_turn_on(self, **kwargs) -> None:
        """Turn this relay channel on."""
        await self.coordinator.client.set_state(on=True, channel=self._channel)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn this relay channel off."""
        await self.coordinator.client.set_state(on=False, channel=self._channel)
        await self.coordinator.async_request_refresh()