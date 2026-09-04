"""Support for the Ai-Thinker WB2 radar gate energy sensors."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    RADAR_GATE_DATA_ENABLE,
    model_to_prefix,
    short_mac,
)
from .coordinator import Wb2Coordinator

# Gate configuration: (field_name, gate_index, distance_range)
GATE_CONFIG = [
    ("g0", 0, "0-75cm"),
    ("g1", 1, "75-150cm"),
    ("g2", 2, "150-225cm"),
    ("g3", 3, "225-300cm"),
    ("g4", 4, "300-375cm"),
    ("g5", 5, "375-450cm"),
    ("g6", 6, "450-525cm"),
    ("g7", 7, "525-600cm"),
]

# Debug counters: (field_name, label)
DEBUG_CONFIG = [
    ("scnt", "TCP轮询次数"),
    ("mcnt", "雷达回调次数"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the WB2 radar gate sensors from a config entry."""
    dtype: str = entry.data.get(CONF_TYPE, DEFAULT_TYPE)
    if dtype != DEVICE_TYPE_RADAR:
        return

    if not RADAR_GATE_DATA_ENABLE:
        return

    coordinator: Wb2Coordinator = hass.data[DOMAIN][entry.entry_id]
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    base_name: str = entry.data.get(CONF_DEVICE_NAME, DEFAULT_NAME)
    mac: str | None = entry.data.get(CONF_MAC)

    device_name = coordinator.data.name if coordinator.data and coordinator.data.name else base_name
    model = coordinator.data.model if coordinator.data and coordinator.data.model else DEFAULT_MODEL
    sw_version = coordinator.data.sw_version if coordinator.data else None

    entities = []
    for field_name, gate_index, distance_range in GATE_CONFIG:
        entities.append(
            Wb2RadarGateSensor(
                coordinator, device_name, model, sw_version, host, port, mac, dtype,
                field_name, gate_index, distance_range,
            )
        )

    for field_name, label in DEBUG_CONFIG:
        entities.append(
            Wb2RadarDebugSensor(
                coordinator, device_name, model, sw_version, host, port, mac, dtype,
                field_name, label,
            )
        )

    async_add_entities(entities)


class Wb2RadarGateSensor(CoordinatorEntity[Wb2Coordinator], SensorEntity):
    """WB2 radar gate energy sensor exposed as a Home Assistant sensor."""

    _attr_has_entity_name = True
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = None

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
        field_name: str,
        gate_index: int,
        distance_range: str,
    ) -> None:
        super().__init__(coordinator)
        self._field_name = field_name
        self._gate_index = gate_index
        self._distance_range = distance_range

        short = short_mac(mac)
        prefix = model_to_prefix(model, dtype)
        if short:
            self.entity_id = f"sensor.{prefix}_{short.lower()}_gate_{gate_index:03d}"
            self._attr_unique_id = f"{DOMAIN}_{mac}_gate_{gate_index}"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_gate_{gate_index}"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        self._attr_name = f"{device_name} 门{gate_index} ({distance_range})"
        self._attr_device_info = {
            "identifiers": identifiers,
            "name": device_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": sw_version,
        }

    @property
    def native_value(self) -> int | None:
        """Return the gate energy value."""
        state = self.coordinator.data
        if state is None:
            return None
        return getattr(state, self._field_name, None)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available


class Wb2RadarDebugSensor(CoordinatorEntity[Wb2Coordinator], SensorEntity):
    """WB2 radar debug counter sensor exposed as a Home Assistant sensor."""

    _attr_has_entity_name = True
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = None

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
        field_name: str,
        label: str,
    ) -> None:
        super().__init__(coordinator)
        self._field_name = field_name

        short = short_mac(mac)
        prefix = model_to_prefix(model, dtype)
        if short:
            self.entity_id = f"sensor.{prefix}_{short.lower()}_{field_name}"
            self._attr_unique_id = f"{DOMAIN}_{mac}_{field_name}"
            identifiers = {(DOMAIN, mac)}
        else:
            self._attr_unique_id = f"{DOMAIN}_{host}_{port}_{field_name}"
            identifiers = {(DOMAIN, f"{host}:{port}")}

        self._attr_name = f"{device_name} {label}"
        self._attr_device_info = {
            "identifiers": identifiers,
            "name": device_name,
            "manufacturer": "Ai-Thinker",
            "model": model,
            "sw_version": sw_version,
        }

    @property
    def native_value(self) -> int | None:
        """Return the debug counter value."""
        state = self.coordinator.data
        if state is None:
            return None
        return getattr(state, self._field_name, None)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and super().available
