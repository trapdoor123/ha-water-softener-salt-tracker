"""Tests for the config flow, options flow and translations."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.translation import async_get_translations

from custom_components.water_softener_salt_tracker.const import (
    CONF_CONSUMPTION_RATE,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DOMAIN,
)

from .conftest import METER, set_meter, setup_entry

NEW_METER = "sensor.new_water_meter"


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

    for field in (CONF_WATER_METER_SENSOR, CONF_MANUFACTURER, CONF_MODEL):
        assert f"{prefix}.config.step.reconfigure.data.{field}" in config
    assert f"{prefix}.config.error.meter_unavailable" in config
    assert f"{prefix}.config.abort.reconfigure_successful" in config

    entity = await async_get_translations(hass, "en", "entity", [DOMAIN])
    for platform, key in (
        ("sensor", "water_processed"),
        ("sensor", "salt_remaining"),
        ("sensor", "salt_level"),
        ("sensor", "last_refill_date"),
        ("button", "reset_salt_level"),
    ):
        assert f"{prefix}.entity.{platform}.{key}.name" in entity

    issues = await async_get_translations(hass, "en", "issues", [DOMAIN])
    assert f"{prefix}.issues.meter_below_baseline.title" in issues
    assert f"{prefix}.issues.meter_below_baseline.description" in issues



async def _start_reconfigure(hass: HomeAssistant, entry):
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    return result


async def test_reconfigure_make_and_model(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)
    result = await _start_reconfigure(hass, entry)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_WATER_METER_SENSOR: METER, CONF_MANUFACTURER: "Harvey", CONF_MODEL: "H20/25"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_MANUFACTURER] == "Harvey"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.manufacturer == "Harvey"
    assert device.model == "H20/25"

    # Clearing the fields removes them again.
    result = await _start_reconfigure(hass, entry)
    await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_WATER_METER_SENSOR: METER}
    )
    await hass.async_block_till_done()
    assert CONF_MANUFACTURER not in entry.data
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.manufacturer is None


async def test_reconfigure_new_meter_keeps_salt_level(hass: HomeAssistant, entry) -> None:
    """Switching meters carries over the water used since the last refill."""
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)
    await set_meter(hass, "3000")  # 2000 L used: 7 kg left
    refill_date = hass.states.get("sensor.water_softener_last_refill_date").state
    hass.states.async_set(NEW_METER, "500000")

    result = await _start_reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_WATER_METER_SENSOR: NEW_METER}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_WATER_METER_SENSOR] == NEW_METER
    assert hass.states.get("sensor.water_softener_salt_remaining").state == "7.0"
    assert hass.states.get("sensor.water_softener_last_refill_date").state == refill_date

    # The old meter no longer affects anything; the new one does.
    await set_meter(hass, "999999")
    assert hass.states.get("sensor.water_softener_salt_remaining").state == "7.0"
    hass.states.async_set(NEW_METER, "502000")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.water_softener_salt_remaining").state == "6.0"


async def test_reconfigure_new_meter_unavailable(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)
    hass.states.async_set(NEW_METER, "unavailable")

    result = await _start_reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_WATER_METER_SENSOR: NEW_METER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_WATER_METER_SENSOR: "meter_unavailable"}
    assert entry.data[CONF_WATER_METER_SENSOR] == METER


async def test_reconfigure_when_old_meter_is_gone(hass: HomeAssistant, entry) -> None:
    """With no old reading, tracking restarts from the new meter's reading."""
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)
    await set_meter(hass, "3000")
    await set_meter(hass, "unavailable")
    hass.states.async_set(NEW_METER, "500000")

    result = await _start_reconfigure(hass, entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_WATER_METER_SENSOR: NEW_METER}
    )
    await hass.async_block_till_done()

    assert result["reason"] == "reconfigure_successful"
    assert hass.states.get("sensor.water_softener_salt_remaining").state == "8.0"
