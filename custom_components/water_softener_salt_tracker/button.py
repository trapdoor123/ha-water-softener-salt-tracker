"""Button platform to reset salt level."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SoftenerConfigEntry
from .entity import SoftenerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoftenerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up reset button."""
    async_add_entities([WaterSoftenerResetButton(entry)])


class WaterSoftenerResetButton(SoftenerEntity, ButtonEntity):
    """Button to reset salt consumption tracking."""

    _attr_icon = "mdi:restore"

    def __init__(self, entry: SoftenerConfigEntry) -> None:
        super().__init__(entry, "reset_salt_level")
        self._attr_unique_id = f"{entry.entry_id}_reset_button"

    async def async_press(self) -> None:
        """Handle button press to snapshot current meter reading."""
        current_reading = self.coordinator.get_meter_reading()
        if current_reading is None:
            # Refuse rather than store a bogus baseline of 0.
            raise HomeAssistantError(
                f"Cannot reset the salt level: water meter "
                f"{self.coordinator.water_meter} has not reported a valid reading "
                "yet. Try again once it has."
            )
        await self.coordinator.async_reset_refill(current_reading)
