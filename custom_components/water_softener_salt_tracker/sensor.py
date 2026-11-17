"""Sensor platform for Water Softener Salt Tracker."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import SoftenerConfigEntry
from .entity import SoftenerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoftenerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities(
        [
            WaterSoftenerProcessedSensor(entry),
            WaterSoftenerSaltRemainingSensor(entry),
            WaterSoftenerSaltLevelSensor(entry),
            WaterSoftenerLastRefillSensor(entry),
        ]
    )


class WaterSoftenerProcessedSensor(SoftenerEntity, SensorEntity):
    """Tracks litres processed since last salt refill."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    def __init__(self, entry: SoftenerConfigEntry) -> None:
        super().__init__(entry, "water_processed")
        self._attr_unique_id = f"{entry.entry_id}_water_processed"

    @property
    def native_value(self) -> float | None:
        water_used = self.coordinator.water_used
        if water_used is None:
            return None
        return round(water_used, 1)


class WaterSoftenerSaltRemainingSensor(SoftenerEntity, SensorEntity):
    """Tracks estimated kg of salt remaining."""

    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, entry: SoftenerConfigEntry) -> None:
        super().__init__(entry, "salt_remaining")
        self._attr_unique_id = f"{entry.entry_id}_salt_remaining"

    @property
    def native_value(self) -> float | None:
        remaining = self.coordinator.salt_remaining
        if remaining is None:
            return None
        return round(remaining, 2)


class WaterSoftenerSaltLevelSensor(SoftenerEntity, SensorEntity):
    """Tracks estimated salt level as percentage."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:gauge"

    def __init__(self, entry: SoftenerConfigEntry) -> None:
        super().__init__(entry, "salt_level")
        self._attr_unique_id = f"{entry.entry_id}_salt_level"

    @property
    def native_value(self) -> float | None:
        remaining = self.coordinator.salt_remaining
        if remaining is None:
            return None
        capacity = self.coordinator.salt_capacity
        if capacity <= 0:
            return 0.0
        return round((remaining / capacity) * 100, 1)


class WaterSoftenerLastRefillSensor(SoftenerEntity, SensorEntity):
    """Displays date of last salt refill."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-check"

    def __init__(self, entry: SoftenerConfigEntry) -> None:
        super().__init__(entry, "last_refill_date")
        self._attr_unique_id = f"{entry.entry_id}_last_refill"

    @property
    def native_value(self) -> date | None:
        if self.coordinator.last_refill_date is None:
            return None
        return dt_util.parse_date(self.coordinator.last_refill_date)
