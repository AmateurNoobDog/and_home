"""Support for Ai-Thinker WB2 button entities (radar + event devices)."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    DEFAULT_TYPE,
    DEVICE_TYPE_EVENT,
    DEVICE_TYPE_RADAR,
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
    """Set up WB2 button entities from a config entry."""
    dtype: str = entry.data.get(CONF_TYPE, DEFAULT_TYPE)
    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    base_name: str = entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
    mac: str | None = entry.data.get(CONF_MAC)

    device_name = coordinator.data.name if coordinator.data and coordinator.data.name else base_name
    model = coordinator.data.model if coordinator.data and coordinator.data.model else DEFAULT_MODEL
    sw_version = coordinator.data.sw_version if coordinator.data else None
    prefix = model_to_prefix(model, dtype)

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
        "sw_version": sw_version,
    }

    if dtype == DEVICE_TYPE_RADAR:
        entities = [
            Wb2CalibrateButton(coordinator, device_name, mac, host, port, device_info, prefix),
            Wb2RestoreButton(coordinator, device_name, mac, host, port, device_info, prefix),
        ]
        async_add_entities(entities)
    elif dtype == DEVICE_TYPE_EVENT:
        entities = [
            Wb2PairButton(coordinator, device_name, mac, host, port, device_info, prefix),
            Wb2ResetButton(coordinator, device_name, mac, host, port, device_info, prefix),
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
        prefix: str,
    ) -> None:
        self.coordinator = coordinator
        short = short_mac(mac)
        if short:
            self.entity_id = f"button.{prefix}_{short.lower()}_calibrate"
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
        prefix: str,
    ) -> None:
        self.coordinator = coordinator
        short = short_mac(mac)
        if short:
            self.entity_id = f"button.{prefix}_{short.lower()}_restore"
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


class Wb2PairButton(CoordinatorEntity[Wb2Coordinator], ButtonEntity):
    """Button to trigger 433 module pair mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:remote"

    def __init__(
        self,
        coordinator: Wb2Coordinator,
        device_name: str,
        mac: str | None,
        host: str,
        port: int,
        device_info: dict,
        prefix: str,
    ) -> None:
        super().__init__(coordinator)
        short = short_mac(mac)
        if short:
            self.entity_id = f"button.{prefix}_{short.lower()}_pair"
            self._attr_unique_id = f"{DOMAIN}_{mac}_pair"
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_pair"
        self._attr_name = f"{device_name} 配对"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Send pair command."""
        await self.coordinator.client.set_state(cmd="pair")
        _LOGGER.debug("Pair button pressed")


class Wb2ResetButton(CoordinatorEntity[Wb2Coordinator], ButtonEntity):
    """Button to reset 433 module pairings."""

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
        prefix: str,
    ) -> None:
        super().__init__(coordinator)
        short = short_mac(mac)
        if short:
            self.entity_id = f"button.{prefix}_{short.lower()}_reset"
            self._attr_unique_id = f"{DOMAIN}_{mac}_reset"
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_reset"
        self._attr_name = f"{device_name} 重置"
        self._attr_device_info = device_info

    async def async_press(self) -> None:
        """Send reset command."""
        await self.coordinator.client.set_state(cmd="reset")
        _LOGGER.debug("Reset button pressed")
