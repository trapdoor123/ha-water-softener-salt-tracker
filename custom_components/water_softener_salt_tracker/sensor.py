"""Sensor platform for Water Softener Salt Tracker."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CONSUMPTION_RATE,
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DEFAULT_CONSUMPTION_RATE,
    DEFAULT_SALT_CAPACITY,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    water_meter = entry.data[CONF_WATER_METER_SENSOR]

    entities = [
        WaterSoftenerProcessedSensor(coordinator, entry, water_meter),
        WaterSoftenerSaltRemainingSensor(coordinator, entry, water_meter),
        WaterSoftenerSaltLevelSensor(coordinator, entry, water_meter),
        WaterSoftenerLastRefillSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class BaseSoftenerSensor(SensorEntity):
    """Base class for softener entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
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

    def _get_current_meter_value(self, entity_id: str) -> float:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return self.coordinator.baseline_reading
        try:
            return float(state.state)
        except ValueError:
            return self.coordinator.baseline_reading


class WaterSoftenerProcessedSensor(BaseSoftenerSensor):
    """Tracks litres processed since last salt refill."""

    _attr_name = "Water Processed Since Refill"
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfVolume.LITERS

    def __init__(self, coordinator, entry: ConfigEntry, water_meter: str) -> None:
        super().__init__(coordinator, entry)
        self._water_meter = water_meter
        self._attr_unique_id = f"{entry.entry_id}_water_processed"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._water_meter], self._on_meter_update
            )
        )

    @callback
    def _on_meter_update(self, event) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        current = self._get_current_meter_value(self._water_meter)
        return max(round(current - self.coordinator.baseline_reading, 1), 0.0)


class WaterSoftenerSaltRemainingSensor(BaseSoftenerSensor):
    """Tracks estimated kg of salt remaining."""

    _attr_name = "Salt Remaining"
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator, entry: ConfigEntry, water_meter: str) -> None:
        super().__init__(coordinator, entry)
        self._water_meter = water_meter
        self._attr_unique_id = f"{entry.entry_id}_salt_remaining"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._water_meter], self._on_meter_update
            )
        )

    @callback
    def _on_meter_update(self, event) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        capacity = self.entry.options.get(
            CONF_SALT_CAPACITY,
            self.entry.data.get(CONF_SALT_CAPACITY, DEFAULT_SALT_CAPACITY),
        )
        rate = (
            self.entry.options.get(
                CONF_CONSUMPTION_RATE,
                self.entry.data.get(CONF_CONSUMPTION_RATE, DEFAULT_CONSUMPTION_RATE),
            )
            / 1000.0
        )
        current = self._get_current_meter_value(self._water_meter)
        water_used = max(current - self.coordinator.baseline_reading, 0.0)
        remaining = capacity - (water_used * rate)
        return max(round(remaining, 2), 0.0)


class WaterSoftenerSaltLevelSensor(BaseSoftenerSensor):
    """Tracks estimated salt level as percentage."""

    _attr_name = "Salt Level"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator, entry: ConfigEntry, water_meter: str) -> None:
        super().__init__(coordinator, entry)
        self._water_meter = water_meter
        self._attr_unique_id = f"{entry.entry_id}_salt_level"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._water_meter], self._on_meter_update
            )
        )

    @callback
    def _on_meter_update(self, event) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        capacity = self.entry.options.get(
            CONF_SALT_CAPACITY,
            self.entry.data.get(CONF_SALT_CAPACITY, DEFAULT_SALT_CAPACITY),
        )
        if capacity <= 0:
            return 0.0
        rate = (
            self.entry.options.get(
                CONF_CONSUMPTION_RATE,
                self.entry.data.get(CONF_CONSUMPTION_RATE, DEFAULT_CONSUMPTION_RATE),
            )
            / 1000.0
        )
        current = self._get_current_meter_value(self._water_meter)
        water_used = max(current - self.coordinator.baseline_reading, 0.0)
        remaining = max(capacity - (water_used * rate), 0.0)
        return max(round((remaining / capacity) * 100, 1), 0.0)


class WaterSoftenerLastRefillSensor(BaseSoftenerSensor):
    """Displays date of last salt refill."""

    _attr_name = "Last Refill Date"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_refill"

    @property
    def native_value(self) -> str:
        return self.coordinator.last_refill_date
