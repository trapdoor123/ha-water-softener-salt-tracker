"""Tests for baseline handling and the salt calculations."""
from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.water_softener_salt_tracker.const import DOMAIN

from .conftest import (
    RESET_BUTTON,
    sensor_state,
    set_meter,
    setup_entry,
    storage_key,
)

ALL_SENSORS = (
    "salt_level",
    "salt_remaining",
    "water_processed_since_refill",
    "last_refill_date",
)


def stored(hass_storage, entry: MockConfigEntry, baseline: float, date: str) -> None:
    """Pre-populate the Store as if a refill had been recorded earlier."""
    hass_storage[storage_key(entry)] = {
        "version": 1,
        "minor_version": 1,
        "key": storage_key(entry),
        "data": {"baseline_reading": baseline, "last_refill_date": date},
    }


async def press_reset(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": RESET_BUTTON}, blocking=True
    )
    await hass.async_block_till_done()


async def test_fresh_install_starts_full(hass: HomeAssistant, entry) -> None:
    """The first meter reading becomes the baseline, so salt starts at 100%."""
    await set_meter(hass, "36737")
    await setup_entry(hass, entry)

    assert sensor_state(hass, "salt_level") == "100.0"
    assert sensor_state(hass, "salt_remaining") == "8.0"
    assert sensor_state(hass, "water_processed_since_refill") == "0.0"
    assert sensor_state(hass, "last_refill_date") == dt_util.now().strftime("%Y-%m-%d")


async def test_salt_calculation(hass: HomeAssistant, entry) -> None:
    """Salt falls in proportion to water metered since the baseline."""
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    await set_meter(hass, "3000")  # 2000 L at 0.5 g/L = 1 kg
    assert sensor_state(hass, "water_processed_since_refill") == "2000.0"
    assert sensor_state(hass, "salt_remaining") == "7.0"
    assert sensor_state(hass, "salt_level") == "87.5"


async def test_salt_never_goes_negative(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "0")
    await setup_entry(hass, entry)

    await set_meter(hass, "100000")
    assert sensor_state(hass, "salt_remaining") == "0.0"
    assert sensor_state(hass, "salt_level") == "0.0"


async def test_first_baseline_is_persisted(
    hass: HomeAssistant, hass_storage, entry
) -> None:
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()

    assert hass_storage[storage_key(entry)]["data"]["baseline_reading"] == 1000.0


async def test_meter_missing_at_startup(hass: HomeAssistant, entry) -> None:
    """With no meter state the sensors are unknown, then start once it appears."""
    await setup_entry(hass, entry)
    for name in ALL_SENSORS:
        assert sensor_state(hass, name) == "unknown"

    await set_meter(hass, "unavailable")
    assert sensor_state(hass, "salt_level") == "unknown"

    await set_meter(hass, "5000")
    assert sensor_state(hass, "salt_level") == "100.0"
    assert sensor_state(hass, "last_refill_date") != "unknown"


async def test_stored_baseline_is_restored(
    hass: HomeAssistant, hass_storage, entry
) -> None:
    stored(hass_storage, entry, 1000.0, "2026-08-15")
    await set_meter(hass, "3000")
    await setup_entry(hass, entry)

    assert sensor_state(hass, "water_processed_since_refill") == "2000.0"
    assert sensor_state(hass, "last_refill_date") == "2026-08-15"


@pytest.mark.parametrize("bad_state", ["unavailable", "unknown", "nan", "inf", "abc"])
async def test_unusable_meter_gives_unknown(
    hass: HomeAssistant, hass_storage, entry, bad_state: str
) -> None:
    """An unusable meter must not look like a full tank or reset the water sensor."""
    stored(hass_storage, entry, 1000.0, "2026-08-15")
    await set_meter(hass, "3000")
    await setup_entry(hass, entry)

    await set_meter(hass, bad_state)
    for name in ("salt_level", "salt_remaining", "water_processed_since_refill"):
        assert sensor_state(hass, name) == "unknown"
    assert sensor_state(hass, "last_refill_date") == "2026-08-15"

    await set_meter(hass, "3000")
    assert sensor_state(hass, "salt_remaining") == "7.0"


async def test_reset_button(hass: HomeAssistant, hass_storage, entry) -> None:
    stored(hass_storage, entry, 1000.0, "2026-08-15")
    await set_meter(hass, "5000")
    await setup_entry(hass, entry)
    assert sensor_state(hass, "salt_level") == "75.0"

    await press_reset(hass)

    assert sensor_state(hass, "salt_level") == "100.0"
    assert sensor_state(hass, "water_processed_since_refill") == "0.0"
    assert sensor_state(hass, "last_refill_date") == dt_util.now().strftime("%Y-%m-%d")
    data = hass_storage[storage_key(entry)]["data"]
    assert data["baseline_reading"] == 5000.0


async def test_reset_button_refuses_without_meter(
    hass: HomeAssistant, hass_storage, entry
) -> None:
    """Pressing reset with no meter reading must not overwrite the baseline."""
    stored(hass_storage, entry, 1000.0, "2026-08-15")
    await set_meter(hass, "5000")
    await setup_entry(hass, entry)

    await set_meter(hass, "unavailable")
    with pytest.raises(HomeAssistantError):
        await press_reset(hass)

    await set_meter(hass, "5000")
    assert sensor_state(hass, "salt_level") == "75.0"
    assert sensor_state(hass, "last_refill_date") == "2026-08-15"


async def test_meter_below_baseline_raises_issue(
    hass: HomeAssistant, entry, caplog: pytest.LogCaptureFixture
) -> None:
    """A meter reset or replacement is flagged, and cleared by a salt reset."""
    await set_meter(hass, "5000")
    await setup_entry(hass, entry)
    issues = ir.async_get(hass)
    issue_id = f"meter_below_baseline_{entry.entry_id}"
    assert issues.async_get_issue(DOMAIN, issue_id) is None

    await set_meter(hass, "12")
    assert issues.async_get_issue(DOMAIN, issue_id) is not None
    assert "below the stored refill baseline" in caplog.text
    assert sensor_state(hass, "water_processed_since_refill") == "0.0"

    await press_reset(hass)
    assert issues.async_get_issue(DOMAIN, issue_id) is None
    assert sensor_state(hass, "salt_level") == "100.0"


async def test_meter_recovering_clears_issue(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "5000")
    await setup_entry(hass, entry)
    issues = ir.async_get(hass)
    issue_id = f"meter_below_baseline_{entry.entry_id}"

    await set_meter(hass, "12")
    assert issues.async_get_issue(DOMAIN, issue_id) is not None

    await set_meter(hass, "5001")
    assert issues.async_get_issue(DOMAIN, issue_id) is None


async def test_options_override_and_reload(hass: HomeAssistant, entry) -> None:
    """Changing options reloads the entry and keeps the baseline."""
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)
    await set_meter(hass, "3000")

    hass.config_entries.async_update_entry(
        entry, options={"salt_capacity": 10.0, "consumption_rate": 1.0}
    )
    await hass.async_block_till_done()

    assert sensor_state(hass, "salt_remaining") == "8.0"
    assert sensor_state(hass, "salt_level") == "80.0"


async def test_unload(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert sensor_state(hass, "salt_level") == "unavailable"
