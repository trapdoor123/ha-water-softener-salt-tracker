"""Button platform to reset salt level."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_WATER_METER_SENSOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up reset button."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    water_meter = entry.data[CONF_WATER_METER_SENSOR]
    async_add_entities([WaterSoftenerResetButton(coordinator, entry, water_meter)])


class WaterSoftenerResetButton(ButtonEntity):
    """Button to reset salt consumption tracking."""

    _attr_has_entity_name = True
    _attr_name = "Reset Salt Level"
    _attr_icon = "mdi:restore"

    def __init__(self, coordinator, entry: ConfigEntry, water_meter: str) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._water_meter = water_meter
        self._attr_unique_id = f"{entry.entry_id}_reset_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
        )

    async def async_press(self) -> None:
        """Handle button press to snapshot current meter reading."""
        state = self.hass.states.get(self._water_meter)
        current_reading = 0.0
        if state is not None and state.state not in ("unknown", "unavailable"):
            try:
                current_reading = float(state.state)
            except ValueError:
                pass
        await self.coordinator.async_reset_refill(current_reading)
