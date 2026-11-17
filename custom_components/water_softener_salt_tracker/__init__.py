"""The Water Softener Salt Tracker integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import SoftenerConfigEntry, SoftenerDataCoordinator, create_store

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: SoftenerConfigEntry) -> bool:
    """Set up Water Softener Salt Tracker from a config entry."""
    coordinator = SoftenerDataCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_start())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: SoftenerConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SoftenerConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Write out any reading still waiting for its delayed save, so it
        # cannot land later and overwrite what the reloaded entry saves.
        coordinator = entry.runtime_data
        await coordinator.store.async_save(coordinator.data_to_save())
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored baseline and any repair issue when the entry is removed."""
    await create_store(hass, entry).async_remove()
    ir.async_delete_issue(hass, DOMAIN, f"meter_below_baseline_{entry.entry_id}")
