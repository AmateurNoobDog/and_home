"""Switch entities for Ai-Thinker WB2 devices (data-driven by entity id)."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Wb2Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for edef in coordinator.device_info.entities:
        if edef.type == "switch":
            entities.append(Wb2Switch(coordinator, edef))
    async_add_entities(entities)


class Wb2Switch(CoordinatorEntity[Wb2Coordinator], SwitchEntity):
    """Switch entity driven by device-reported entity definition."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Wb2Coordinator, edef) -> None:
        super().__init__(coordinator)
        self._entity_id = edef.id
        self._attr_unique_id = f"{DOMAIN}_{edef.id}"
        self._attr_name = edef.name
        self._attr_icon = edef.icon
        self._attr_device_info = _device_info(coordinator)

    def _get_entity_data(self) -> dict:
        state = self.coordinator.data
        if state is None:
            return {}
        entity_state = state.find_entity(self._entity_id)
        if entity_state is None:
            return {}
        return entity_state.data

    @property
    def is_on(self) -> bool | None:
        data = self._get_entity_data()
        if not data:
            return None
        on = data.get("on")
        if on is None:
            return None
        return bool(on)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available

    async def async_turn_on(self, **kwargs) -> None:
        state = await self.coordinator.client.set_state(
            entity_id=self._entity_id, params={"on": 1}
        )
        self.coordinator.async_set_updated_data(state)

    async def async_turn_off(self, **kwargs) -> None:
        state = await self.coordinator.client.set_state(
            entity_id=self._entity_id, params={"on": 0}
        )
        self.coordinator.async_set_updated_data(state)


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
