"""Event entity for Ai-Thinker event devices (e.g. 433 remote receiver)."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
    DEFAULT_TYPE,
    DOMAIN,
    model_to_prefix,
    short_mac,
)
from .coordinator import Wb2Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WB2 event entity from a config entry."""
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    base_name: str = entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
    mac: str | None = entry.data.get(CONF_MAC)
    dtype: str = entry.data.get(CONF_TYPE, DEFAULT_TYPE)

    device_name = coordinator.data.name if coordinator.data and coordinator.data.name else base_name
    model = coordinator.data.model if coordinator.data and coordinator.data.model else DEFAULT_MODEL
    sw_version = coordinator.data.sw_version if coordinator.data else None

    async_add_entities([
        Wb2EventEntity(
            coordinator, device_name, model, sw_version, host, port, mac, dtype
        )
    ])


class Wb2EventEntity(CoordinatorEntity[Wb2Coordinator], EventEntity):
    """Event entity that fires HA events when device pushes press/release."""

    _attr_has_entity_name = False
    _attr_device_class = None
    _attr_event_types = ["press", "release"]

    def __init__(
        self,
        coordinator: Wb2Coordinator,
        device_name: str,
        model: str,
        sw_version: str | None,
        host: str,
        port: int,
        mac: str | None,
        dtype: str,
    ) -> None:
        super().__init__(coordinator)
        short = short_mac(mac)
        prefix = model_to_prefix(model, dtype)
        if short:
            self.entity_id = f"event.{prefix}_{short.lower()}_event"
            self._attr_unique_id = f"{DOMAIN}_{mac}_event"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_event"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        self._attr_name = "键值"
        self._last_event_type: str | None = None
        self._last_key: str | None = None

        self._attr_device_info = {
            "identifiers": identifiers,
            "name": device_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": sw_version,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        state = self.coordinator.data
        if state is None:
            return

        event_type = getattr(state, "event", None)
        key = getattr(state, "key", None)

        if event_type and key:
            if event_type != self._last_event_type or key != self._last_key:
                self._last_event_type = event_type
                self._last_key = key
                # Call base class _trigger_event to update entity state
                super()._trigger_event(event_type, {"event_id": key})
                # Also fire custom bus event for automations
                if self.hass is not None:
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_{self._attr_unique_id}",
                        {"event_type": event_type, "event_id": key},
                    )
                    _LOGGER.debug("Fired event %s: %s", event_type, key)

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        return {
            "last_key": self._last_key,
            "last_event": self._last_event_type,
        }
