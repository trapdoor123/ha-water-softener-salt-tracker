"""Base entity for Water Softener Salt Tracker."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CONF_MANUFACTURER, CONF_MODEL, DOMAIN
from .coordinator import SoftenerConfigEntry, SoftenerDataCoordinator


class SoftenerEntity(Entity):
    """An entity belonging to one water softener device.

    The coordinator calls every registered listener when the water meter
    changes or the salt level is reset.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: SoftenerConfigEntry, key: str) -> None:
        self.coordinator: SoftenerDataCoordinator = entry.runtime_data
        self.entry = entry
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            # Optional, user-supplied in the config flow. None clears any
            # value an earlier version set on the device.
            manufacturer=entry.data.get(CONF_MANUFACTURER) or None,
            model=entry.data.get(CONF_MODEL) or None,
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.coordinator.listeners.append(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callbacks."""
        if self.async_write_ha_state in self.coordinator.listeners:
            self.coordinator.listeners.remove(self.async_write_ha_state)
