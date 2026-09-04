"""Support for the Ai-Thinker WB2 RGB LED light."""

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
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
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
    DEVICE_TYPE_LIGHT,
    DOMAIN,
    model_to_prefix,
    short_mac,
)
from .coordinator import Wb2Coordinator

_LEVEL_MAX = 255


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WB2 RGB light from a config entry."""
    dtype: str = entry.data.get(CONF_TYPE, DEFAULT_TYPE)
    if dtype != DEVICE_TYPE_LIGHT:
        return
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    base_name: str = entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
    mac: str | None = entry.data.get(CONF_MAC)

    seq = _next_sequence(hass, mac, dtype, model)
    device_name = coordinator.data.name if coordinator.data and coordinator.data.name else base_name
    model = coordinator.data.model if coordinator.data and coordinator.data.model else DEFAULT_MODEL
    sw_version = coordinator.data.sw_version if coordinator.data else None
    async_add_entities(
        [Wb2Light(coordinator, device_name, model, sw_version, host, port, mac, dtype, seq)]
    )


def _next_sequence(hass: HomeAssistant, mac: str | None, dtype: str, model: str | None = None) -> int:
    """Return the next entity sequence number for (mac, light)."""
    if not mac:
        return 1
    prefix = f"light.{model_to_prefix(model, dtype)}_{short_mac(mac).lower()}_light_"
    seq = 1
    for entity in async_get_entity_registry(hass).entities.values():
        eid = entity.entity_id or ""
        suffix = eid[len(prefix) :]
        if eid.startswith(prefix) and suffix.isdigit():
            seq = max(seq, int(suffix) + 1)
    return seq


class Wb2Light(CoordinatorEntity[Wb2Coordinator], LightEntity):
    """The WB2 RGB LED exposed as a Home Assistant light."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_brightness_step = 1

    def __init__(
        self,
        coordinator: Wb2Coordinator,
        base_name: str,
        model: str,
        sw_version: str | None,
        host: str,
        port: int,
        mac: str | None,
        dtype: str,
        seq: int,
    ) -> None:
        super().__init__(coordinator)
        short = short_mac(mac)
        prefix = model_to_prefix(model, dtype)
        if short:
            self.entity_id = f"light.{prefix}_{short.lower()}_light_{seq:03d}"
            self._attr_unique_id = f"{DOMAIN}_{mac}_light"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_light"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        self._attr_device_info = {
            "identifiers": identifiers,
            "name": base_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": sw_version,
        }
        self._last_color: tuple[int, int, int] = (255, 255, 255)

    def _handle_coordinator_update(self) -> None:
        state = self.coordinator.data
        if state is not None and (state.r or state.g or state.b):
            self._last_color = (state.r, state.g, state.b)
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data
        if state is None:
            return None
        return state.r > 0 or state.g > 0 or state.b > 0

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        state = self.coordinator.data
        if state is None:
            return (0, 0, 0)
        return (state.r, state.g, state.b)

    @property
    def brightness(self) -> int | None:
        state = self.coordinator.data
        if state is None:
            return None
        return max(state.r, state.g, state.b)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on with optional color/brightness."""
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
            self._last_color = (r, g, b)
        else:
            r, g, b = self._last_color

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if brightness <= 0:
                brightness = _LEVEL_MAX
            current = max(r, g, b)
            if current == 0:
                r = g = b = brightness
            else:
                scale = brightness / current
                r = min(255, round(r * scale))
                g = min(255, round(g * scale))
                b = min(255, round(b * scale))
            if r == 0 and g == 0 and b == 0:
                r = g = b = brightness
        elif r == 0 and g == 0 and b == 0:
            r = g = b = _LEVEL_MAX

        self._last_color = (r, g, b)
        await self.coordinator.client.set_state(r=r, g=g, b=b)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self.coordinator.client.set_state(r=0, g=0, b=0)
        await self.coordinator.async_request_refresh()