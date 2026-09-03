"""Support for Ai-Thinker WB2 radar button entities."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_NAME,
    CONF_HOST,
    CONF_MAC,
    CONF_PORT,
    CONF_TYPE,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_TYPE,
    DEVICE_TYPE_RADAR,
    DOMAIN,
    short_mac,
)
from .coordinator import Wb2Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WB2 radar button entities from a config entry."""
    dtype: str = entry.data.get(CONF_TYPE, DEFAULT_TYPE)
    if dtype != DEVICE_TYPE_RADAR:
        return

    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    base_name: str = entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
    mac: str | None = entry.data.get(CONF_MAC)

    device_name = coordinator.data.name if coordinator.data and coordinator.data.name else base_name
    model = coordinator.data.model if coordinator.data and coordinator.data.model else DEFAULT_MODEL

    short = short_mac(mac)
    if short:
        identifiers = {(DOMAIN, mac)}
    else:
        identifiers = {(DOMAIN, f"{host}:{port}")}

    device_info = {
        "identifiers": identifiers,
        "name": device_name,
        "manufacturer": "Ai-Thinker",
        "model": model,
        "sw_version": "0.7.0",
    }

    entities = [
        Wb2CalibrateButton(coordinator, device_name, mac, host, port, device_info),
        Wb2RestoreButton(coordinator, device_name, mac, host, port, device_info),
    ]
    async_add_entities(entities)


class Wb2CalibrateButton(ButtonEntity):
    """Button to calibrate radar with current environment (no person)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:cog-counterclockwise"

    def __init__(
        self,
        coordinator: Wb2Coordinator,
        device_name: str,
        mac: str | None,
        host: str,
        port: int,
        device_info: dict,
    ) -> None:
        self.coordinator = coordinator
        short = short_mac(mac)
        if short:
            self.entity_id = f"button.{DOMAIN}_{short.lower()}_calibrate"
            self._attr_unique_id = f"{DOMAIN}_{mac}_calibrate"
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_calibrate"
        self._attr_name = f"{device_name} 标定无人"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Handle button press."""
        try:
            result = await self.coordinator.async_calibrate()
            _LOGGER.info("Calibrate result: %s", result)
        except Exception as err:
            _LOGGER.error("Calibrate failed: %s", err)


class Wb2RestoreButton(ButtonEntity):
    """Button to restore radar default parameters."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:restore"

    def __init__(
        self,
        coordinator: Wb2Coordinator,
        device_name: str,
        mac: str | None,
        host: str,
        port: int,
        device_info: dict,
    ) -> None:
        self.coordinator = coordinator
        short = short_mac(mac)
        if short:
            self.entity_id = f"button.{DOMAIN}_{short.lower()}_restore"
            self._attr_unique_id = f"{DOMAIN}_{mac}_restore"
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_restore"
        self._attr_name = f"{device_name} 恢复默认参数"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Handle button press."""
        try:
            result = await self.coordinator.async_restore_defaults()
            _LOGGER.info("Restore defaults result: %s", result)
        except Exception as err:
            _LOGGER.error("Restore defaults failed: %s", err)
