"""Sensor entities for AND WB2 devices (data-driven by entity id)."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, device_info
from .coordinator import Wb2Coordinator

# Device class mapping from protocol string to HA SensorDeviceClass
DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "pressure": SensorDeviceClass.ATMOSPHERIC_PRESSURE,
    "battery": SensorDeviceClass.BATTERY,
    "co2": SensorDeviceClass.CO2,
    "pm25": SensorDeviceClass.PM25,
}

# Unit mapping from protocol string to HA unit constants
UNIT_MAP = {
    "°C": UnitOfTemperature.CELSIUS,
    "°F": UnitOfTemperature.FAHRENHEIT,
    "%": PERCENTAGE,
    "hPa": UnitOfPressure.HPA,
}

# Device classes that support measurement state class for long-term statistics
MEASUREMENT_DEVICE_CLASSES = {
    SensorDeviceClass.TEMPERATURE,
    SensorDeviceClass.HUMIDITY,
    SensorDeviceClass.ATMOSPHERIC_PRESSURE,
    SensorDeviceClass.PM25,
    SensorDeviceClass.CO2,
}


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

        # Set device class from entity definition
        if edef.device_class:
            self._attr_device_class = DEVICE_CLASS_MAP.get(edef.device_class)

        # Set unit from entity definition
        if edef.unit:
            self._attr_native_unit_of_measurement = UNIT_MAP.get(edef.unit, edef.unit)

        # Set state class for measurement device classes (enables long-term statistics)
        if self._attr_device_class in MEASUREMENT_DEVICE_CLASSES:
            self._attr_state_class = SensorStateClass.MEASUREMENT

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
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
