"""Support for the Ai-Thinker WB2 radar presence/motion binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    DEVICE_TYPE_RADAR,
    DOMAIN,
    model_to_prefix,
    short_mac,
)
from .coordinator import Wb2Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WB2 radar binary sensors from a config entry."""
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
    sw_version = coordinator.data.sw_version if coordinator.data else None

    async_add_entities(
        [
            Wb2RadarPresence(coordinator, device_name, model, sw_version, host, port, mac, dtype),
            Wb2RadarMotion(coordinator, device_name, model, sw_version, host, port, mac, dtype),
        ]
    )


class Wb2RadarPresence(CoordinatorEntity[Wb2Coordinator], BinarySensorEntity):
    """WB2 radar presence sensor exposed as a Home Assistant binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

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
            self.entity_id = f"binary_sensor.{prefix}_{short.lower()}_presence_001"
            self._attr_unique_id = f"{DOMAIN}_{mac}_presence"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_presence"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        self._attr_name = f"{device_name} 存在检测"
        self._attr_device_info = {
            "identifiers": identifiers,
            "name": device_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": sw_version,
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if presence is detected."""
        state = self.coordinator.data
        if state is None:
            return None
        if state.presence is None:
            return None
        return bool(state.presence)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available


class Wb2RadarMotion(CoordinatorEntity[Wb2Coordinator], BinarySensorEntity):
    """WB2 radar motion sensor exposed as a Home Assistant binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.MOTION

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
            self.entity_id = f"binary_sensor.{prefix}_{short.lower()}_motion_001"
            self._attr_unique_id = f"{DOMAIN}_{mac}_motion"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_motion"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        self._attr_name = f"{device_name} 运动检测"
        self._attr_device_info = {
            "identifiers": identifiers,
            "name": device_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": sw_version,
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if motion is detected."""
        state = self.coordinator.data
        if state is None:
            return None
        if state.motion is None:
            return None
        return bool(state.motion)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available
