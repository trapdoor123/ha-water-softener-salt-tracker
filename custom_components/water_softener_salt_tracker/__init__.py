"""The Water Softener Salt Tracker integration."""
from __future__ import annotations

from datetime import datetime
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


class SoftenerDataCoordinator:
    """Manages baseline meter persistence and listener state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        self.baseline_reading: float = 0.0
        self.last_refill_date: str = datetime.now().strftime("%Y-%m-%d")
        self.listeners: list = []

    async def async_load(self) -> None:
        """Load stored baseline values."""
        data = await self.store.async_load()
        if data:
            self.baseline_reading = data.get("baseline_reading", 0.0)
            self.last_refill_date = data.get("last_refill_date", datetime.now().strftime("%Y-%m-%d"))

    async def async_reset_refill(self, current_reading: float) -> None:
        """Update baseline reading to current meter state."""
        self.baseline_reading = current_reading
        self.last_refill_date = datetime.now().strftime("%Y-%m-%d")
        await self.store.async_save(
            {
                "baseline_reading": self.baseline_reading,
                "last_refill_date": self.last_refill_date,
            }
        )
        for listener in self.listeners:
            listener()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Water Softener Salt Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = SoftenerDataCoordinator(hass, entry)
    await coordinator.async_load()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
