"""Button platform to reset salt level."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SoftenerDataCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up reset button."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WaterSoftenerResetButton(coordinator, entry)])


class WaterSoftenerResetButton(ButtonEntity):
    """Button to reset salt consumption tracking."""

    _attr_has_entity_name = True
    _attr_name = "Reset Salt Level"
    _attr_icon = "mdi:restore"

    def __init__(self, coordinator: SoftenerDataCoordinator, entry: ConfigEntry) -> None:
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reset_button"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
        )

    async def async_press(self) -> None:
        """Handle button press to snapshot current meter reading."""
        current_reading = self.coordinator.get_meter_reading()
        if current_reading is None:
            # Refuse rather than store a bogus baseline of 0.
            raise HomeAssistantError(
                f"Cannot reset the salt level: water meter "
                f"{self.coordinator.water_meter} has no valid reading right now. "
                "Try again once it is available."
            )
        await self.coordinator.async_reset_refill(current_reading)
