"""Sensor entities for AND WB2 devices (data-driven by entity id)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, device_info
from .coordinator import Wb2Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for edef in coordinator.device_info.entities:
        if edef.type == "sensor":
            entities.append(Wb2Sensor(coordinator, edef))
    async_add_entities(entities)


class Wb2Sensor(CoordinatorEntity[Wb2Coordinator], SensorEntity):
    """Sensor entity driven by device-reported entity definition."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Wb2Coordinator, edef) -> None:
        super().__init__(coordinator)
        self._entity_id = edef.id
        self._attr_unique_id = f"{DOMAIN}_{edef.id}"
        self._attr_name = edef.name
        self._attr_icon = edef.icon
        self._attr_device_info = device_info(coordinator)

    @property
    def native_value(self) -> str | None:
        state = self.coordinator.data
        if state is None:
            return None
        entity_state = state.find_entity(self._entity_id)
        if entity_state is None:
            return None
        return str(entity_state.data.get("value", ""))
