"""Light entity for AND WB2 devices (data-driven by entity id)."""

from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
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
        if edef.type == "light":
            entities.append(Wb2Light(coordinator, edef))
    async_add_entities(entities)


class Wb2Light(CoordinatorEntity[Wb2Coordinator], LightEntity):
    """Light entity driven by device-reported entity definition."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, coordinator: Wb2Coordinator, edef) -> None:
        super().__init__(coordinator)
        self._entity_id = edef.id
        self._attr_unique_id = f"{DOMAIN}_{edef.id}"
        self._attr_name = edef.name
        self._attr_icon = edef.icon
        self._attr_device_info = device_info(coordinator)
        self._last_color: tuple[int, int, int] = (255, 255, 255)
        self._last_brightness: int = 255

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
        r = data.get("r", 0)
        g = data.get("g", 0)
        b = data.get("b", 0)
        return r > 0 or g > 0 or b > 0

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        data = self._get_entity_data()
        if not data:
            return (0, 0, 0)
        return (data.get("r", 0), data.get("g", 0), data.get("b", 0))

    @property
    def brightness(self) -> int | None:
        data = self._get_entity_data()
        if not data:
            return None
        b = data.get("brightness")
        if b is not None:
            return b
        return max(data.get("r", 0), data.get("g", 0), data.get("b", 0))

    async def async_turn_on(self, **kwargs) -> None:
        r = g = b = None
        brightness = None

        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]

        if r is None:
            r, g, b = self._last_color
        if brightness is None:
            brightness = self._last_brightness

        self._last_color = (r, g, b)
        self._last_brightness = brightness

        params = {"r": r, "g": g, "b": b, "brightness": brightness}
        state = await self.coordinator.client.set_state(
            entity_id=self._entity_id, params=params
        )
        self.coordinator.async_set_updated_data(state)

    async def async_turn_off(self, **kwargs) -> None:
        params = {"r": 0, "g": 0, "b": 0}
        state = await self.coordinator.client.set_state(
            entity_id=self._entity_id, params=params
        )
        self.coordinator.async_set_updated_data(state)
