"""Number entities for AND TTS devices."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, device_info
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
        if edef.type == "number":
            entities.append(Wb2Number(coordinator, edef))
    async_add_entities(entities)


class Wb2Number(CoordinatorEntity[Wb2Coordinator], NumberEntity):
    """Number entity for volume/speed control."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Wb2Coordinator, edef) -> None:
        super().__init__(coordinator)
        self._entity_id = edef.id
        self._attr_unique_id = f"{DOMAIN}_{edef.id}"
        self._attr_name = edef.name
        self._attr_icon = edef.icon
        self._attr_device_info = device_info(coordinator)

        self._attr_native_min_value = 0
        self._attr_native_max_value = 9
        self._attr_native_step = 1

    @property
    def native_value(self) -> float | None:
        state = self.coordinator.data
        if state is None:
            return None
        entity_state = state.find_entity(self._entity_id)
        if entity_state is None:
            return None
        value = entity_state.data.get("value")
        if value is None:
            return None
        return float(value)

    async def async_set_value(self, value: float) -> None:
        try:
            state = await self.coordinator.client.set_state(
                entity_id=self._entity_id,
                params={"value": int(value)},
            )
            self.coordinator.async_set_updated_data(state)
        except Exception as err:
            _LOGGER.error("Number set failed for %s: %s", self._entity_id, err)
