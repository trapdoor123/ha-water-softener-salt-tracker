"""Tests for the config flow, options flow and translations."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations

from custom_components.water_softener_salt_tracker.const import (
    CONF_CONSUMPTION_RATE,
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DOMAIN,
)

from .conftest import METER, set_meter, setup_entry


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    await set_meter(hass, "1000")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Utility Room Softener",
            CONF_WATER_METER_SENSOR: METER,
            CONF_SALT_CAPACITY: 8.0,
            CONF_CONSUMPTION_RATE: 0.685,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Utility Room Softener"
    assert result["data"][CONF_WATER_METER_SENSOR] == METER
    assert result["data"][CONF_CONSUMPTION_RATE] == 0.685
    assert hass.states.get("sensor.utility_room_softener_salt_level").state == "100.0"


async def test_options_flow(hass: HomeAssistant, entry) -> None:
    """The options form opens (regression test for the v1.0.1 500 error) and saves."""
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SALT_CAPACITY: 10.0, CONF_CONSUMPTION_RATE: 0.4},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_SALT_CAPACITY: 10.0, CONF_CONSUMPTION_RATE: 0.4}
    assert hass.states.get("sensor.water_softener_salt_remaining").state == "10.0"


async def test_translations_load(hass: HomeAssistant) -> None:
    """Form labels and the repair issue text are available to Home Assistant."""
    config = await async_get_translations(hass, "en", "config", [DOMAIN])
    prefix = f"component.{DOMAIN}"
    for field in ("name", CONF_WATER_METER_SENSOR, CONF_SALT_CAPACITY, CONF_CONSUMPTION_RATE):
        assert f"{prefix}.config.step.user.data.{field}" in config

    options = await async_get_translations(hass, "en", "options", [DOMAIN])
    for field in (CONF_SALT_CAPACITY, CONF_CONSUMPTION_RATE):
        assert f"{prefix}.options.step.init.data.{field}" in options

    issues = await async_get_translations(hass, "en", "issues", [DOMAIN])
    assert f"{prefix}.issues.meter_below_baseline.title" in issues
    assert f"{prefix}.issues.meter_below_baseline.description" in issues

