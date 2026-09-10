"""Event entity for Ai-Thinker event devices (data-driven by entity id)."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Wb2Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for edef in coordinator.device_info.entities:
        if edef.type == "event":
            entities.append(Wb2EventEntity(coordinator, edef))
    async_add_entities(entities)


class Wb2EventEntity(CoordinatorEntity[Wb2Coordinator], EventEntity):
    """Event entity that fires HA events when device pushes press/release."""

    _attr_has_entity_name = True
    _attr_event_types = ["press", "release"]

    def __init__(self, coordinator: Wb2Coordinator, edef) -> None:
        super().__init__(coordinator)
        self._entity_id = edef.id
        self._attr_unique_id = f"{DOMAIN}_{edef.id}"
        self._attr_name = edef.name
        self._attr_icon = edef.icon
        self._attr_device_info = _device_info(coordinator)
        self._last_event_type: str | None = None
        self._last_event_id: str | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        state = self.coordinator.data
        if state is None:
            return

        entity_state = state.find_entity(self._entity_id)
        if entity_state is None:
            return

        event_type = entity_state.data.get("event_type")
        event_id = entity_state.data.get("event_id", "")

        if event_type:
            if event_type != self._last_event_type or event_id != self._last_event_id:
                self._last_event_type = event_type
                self._last_event_id = event_id
                super()._trigger_event(event_type, {"event_id": event_id})
                if self.hass is not None:
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_{self._attr_unique_id}",
                        {"event_type": event_type, "event_id": event_id},
                    )

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "last_event_id": self._last_event_id,
            "last_event_type": self._last_event_type,
        }


def _device_info(coordinator: Wb2Coordinator) -> dict:
    info = coordinator.device_info
    mac = info.mac
    return {
        "identifiers": {(DOMAIN, mac)} if mac else {(DOMAIN, info.name)},
        "name": info.name,
        "manufacturer": "Ai-Thinker",
        "model": info.model,
        "sw_version": info.sw_version,
    }
