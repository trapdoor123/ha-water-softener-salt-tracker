"""Sensor platform for Water Softener Salt Tracker."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SoftenerDataCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WaterSoftenerProcessedSensor(coordinator, entry),
        WaterSoftenerSaltRemainingSensor(coordinator, entry),
        WaterSoftenerSaltLevelSensor(coordinator, entry),
        WaterSoftenerLastRefillSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class BaseSoftenerSensor(SensorEntity):
    """Base class for softener entities.

    The coordinator tracks the upstream water meter and calls every registered
    listener when the meter changes or the salt level is reset.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: SoftenerDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Harvey / Generic",
            model="Twin-Tank Metered Softener",
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.coordinator.listeners.append(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callbacks."""
        if self.async_write_ha_state in self.coordinator.listeners:
            self.coordinator.listeners.remove(self.async_write_ha_state)


class WaterSoftenerProcessedSensor(BaseSoftenerSensor):
    """Tracks litres processed since last salt refill."""

    _attr_name = "Water Processed Since Refill"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    def __init__(self, coordinator: SoftenerDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_water_processed"

    @property
    def native_value(self) -> float | None:
        water_used = self.coordinator.water_used
        if water_used is None:
            return None
        return round(water_used, 1)


class WaterSoftenerSaltRemainingSensor(BaseSoftenerSensor):
    """Tracks estimated kg of salt remaining."""

    _attr_name = "Salt Remaining"
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator: SoftenerDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_salt_remaining"

    @property
    def native_value(self) -> float | None:
        remaining = self.coordinator.salt_remaining
        if remaining is None:
            return None
        return round(remaining, 2)


class WaterSoftenerSaltLevelSensor(BaseSoftenerSensor):
    """Tracks estimated salt level as percentage."""

    _attr_name = "Salt Level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator: SoftenerDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
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


class WaterSoftenerLastRefillSensor(BaseSoftenerSensor):
    """Displays date of last salt refill."""

    _attr_name = "Last Refill Date"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: SoftenerDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_refill"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.last_refill_date
