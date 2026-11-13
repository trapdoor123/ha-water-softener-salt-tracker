"""The Water Softener Salt Tracker integration."""
from __future__ import annotations

from collections.abc import Callable
import logging
import math

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CONSUMPTION_RATE,
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DEFAULT_CONSUMPTION_RATE,
    DEFAULT_SALT_CAPACITY,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


class SoftenerDataCoordinator:
    """Tracks the upstream water meter and persists the refill baseline."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.water_meter: str = entry.data[CONF_WATER_METER_SENSOR]
        self.store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        # None until a baseline has been stored or snapshotted from the meter.
        self.baseline_reading: float | None = None
        self.last_refill_date: str | None = None
        self.listeners: list[Callable[[], None]] = []
        self._below_baseline_logged = False

    @property
    def _issue_id(self) -> str:
        return f"meter_below_baseline_{self.entry.entry_id}"

    @property
    def salt_capacity(self) -> float:
        """Configured salt capacity in kg."""
        return self.entry.options.get(
            CONF_SALT_CAPACITY,
            self.entry.data.get(CONF_SALT_CAPACITY, DEFAULT_SALT_CAPACITY),
        )

    @property
    def consumption_rate(self) -> float:
        """Configured salt consumption rate in g/L."""
        return self.entry.options.get(
            CONF_CONSUMPTION_RATE,
            self.entry.data.get(CONF_CONSUMPTION_RATE, DEFAULT_CONSUMPTION_RATE),
        )

    def get_meter_reading(self) -> float | None:
        """Return the upstream meter reading, or None if it has no usable value."""
        state = self.hass.states.get(self.water_meter)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            reading = float(state.state)
        except ValueError:
            return None
        return reading if math.isfinite(reading) else None

    @property
    def water_used(self) -> float | None:
        """Litres metered since the baseline, or None if not currently known."""
        reading = self.get_meter_reading()
        if reading is None or self.baseline_reading is None:
            return None
        return max(reading - self.baseline_reading, 0.0)

    @property
    def salt_remaining(self) -> float | None:
        """Estimated kg of salt remaining, or None if not currently known."""
        water_used = self.water_used
        if water_used is None:
            return None
        used_kg = water_used * (self.consumption_rate / 1000.0)
        return max(self.salt_capacity - used_kg, 0.0)

    async def async_load(self) -> None:
        """Load stored baseline values."""
        data = await self.store.async_load()
        if data:
            self.baseline_reading = data.get("baseline_reading")
            self.last_refill_date = data.get("last_refill_date")

    @callback
    def async_start(self) -> Callable[[], None]:
        """Start tracking the upstream meter. Returns an unsubscribe callback."""
        unsub = async_track_state_change_event(
            self.hass, [self.water_meter], self._handle_meter_event
        )
        self._process_meter_reading()
        return unsub

    @callback
    def _handle_meter_event(self, event: Event) -> None:
        self._process_meter_reading()
        self._notify_listeners()

    @callback
    def _process_meter_reading(self) -> None:
        """Initialise the baseline on first use and watch for meter resets."""
        reading = self.get_meter_reading()
        if reading is None:
            return

        if self.baseline_reading is None:
            # First valid reading since install: start tracking from here
            # rather than counting the meter's lifetime total as salt used.
            self.baseline_reading = reading
            self.last_refill_date = dt_util.now().strftime("%Y-%m-%d")
            self.store.async_delay_save(self._data_to_save, 0)
            _LOGGER.info(
                "%s: starting salt tracking from meter reading %s",
                self.entry.title,
                reading,
            )
            return

        if reading < self.baseline_reading:
            if not self._below_baseline_logged:
                self._below_baseline_logged = True
                _LOGGER.warning(
                    "%s: water meter %s reads %s, below the stored refill "
                    "baseline of %s. The meter may have been reset or replaced; "
                    "salt usage cannot be tracked until the salt level is reset",
                    self.entry.title,
                    self.water_meter,
                    reading,
                    self.baseline_reading,
                )
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="meter_below_baseline",
                translation_placeholders={
                    "name": self.entry.title,
                    "entity_id": self.water_meter,
                    "reading": str(reading),
                    "baseline": str(self.baseline_reading),
                },
            )
        else:
            self._clear_below_baseline()

    @callback
    def _clear_below_baseline(self) -> None:
        self._below_baseline_logged = False
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)

    @callback
    def _data_to_save(self) -> dict[str, float | str | None]:
        return {
            "baseline_reading": self.baseline_reading,
            "last_refill_date": self.last_refill_date,
        }

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self.listeners):
            listener()

    async def async_reset_refill(self, current_reading: float) -> None:
        """Update baseline reading to current meter state."""
        self.baseline_reading = current_reading
        self.last_refill_date = dt_util.now().strftime("%Y-%m-%d")
        await self.store.async_save(self._data_to_save())
        self._clear_below_baseline()
        self._notify_listeners()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Water Softener Salt Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = SoftenerDataCoordinator(hass, entry)
    await coordinator.async_load()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.async_on_unload(coordinator.async_start())

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
