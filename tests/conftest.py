"""Shared fixtures for the Water Softener Salt Tracker tests."""
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Importing the integration here makes sure this repository's
# custom_components package is the one Home Assistant loads.
from custom_components.water_softener_salt_tracker.const import (
    CONF_CONSUMPTION_RATE,
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DOMAIN,
)

METER = "sensor.water_meter"
ENTITY_PREFIX = "sensor.water_softener_"
RESET_BUTTON = "button.water_softener_reset_salt_level"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration under test."""
    return


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """A config entry: 8 kg capacity, 0.5 g/L, so 2000 L uses 1 kg."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Water Softener",
        data={
            "name": "Water Softener",
            CONF_WATER_METER_SENSOR: METER,
            CONF_SALT_CAPACITY: 8.0,
            CONF_CONSUMPTION_RATE: 0.5,
        },
    )
    config_entry.add_to_hass(hass)
    return config_entry


async def setup_entry(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Set up the config entry and wait for it to settle."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def set_meter(hass: HomeAssistant, value: str) -> None:
    """Set the upstream water meter state."""
    hass.states.async_set(METER, value)
    await hass.async_block_till_done()


def sensor_state(hass: HomeAssistant, name: str) -> str:
    """Return the state of one of the integration's sensors."""
    state = hass.states.get(ENTITY_PREFIX + name)
    assert state is not None, f"{ENTITY_PREFIX + name} does not exist"
    return state.state


def storage_key(config_entry: MockConfigEntry) -> str:
    """Return the Store key used for a config entry."""
    return f"{DOMAIN}.storage_{config_entry.entry_id}"
