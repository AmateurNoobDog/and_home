"""Button entities for Ai-Thinker WB2 devices (data-driven by entity id)."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
        if edef.type == "button":
            entities.append(Wb2Button(coordinator, edef))
    async_add_entities(entities)


class Wb2Button(CoordinatorEntity[Wb2Coordinator], ButtonEntity):
    """Button entity driven by device-reported entity definition."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Wb2Coordinator, edef) -> None:
        super().__init__(coordinator)
        self._entity_id = edef.id
        self._action = edef.action
        self._attr_unique_id = f"{DOMAIN}_{edef.id}"
        self._attr_name = edef.name
        self._attr_icon = edef.icon
        self._attr_device_info = _device_info(coordinator)

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.send_cmd(self._action, self._entity_id)
        except Exception as err:
            _LOGGER.error("Button %s failed: %s", self._action, err)


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
