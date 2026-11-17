"""Tests for the device, entity metadata and entry removal."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.water_softener_salt_tracker.const import (
    CONF_MANUFACTURER,
    CONF_MODEL,
    DOMAIN,
)

from .conftest import (
    ENTITY_PREFIX,
    RESET_BUTTON,
    get_device,
    set_meter,
    setup_entry,
    storage_key,
)

ENTITY_IDS = [
    ENTITY_PREFIX + "water_processed_since_refill",
    ENTITY_PREFIX + "salt_remaining",
    ENTITY_PREFIX + "salt_level",
    ENTITY_PREFIX + "last_refill_date",
    RESET_BUTTON,
]


async def test_integration_type_is_device(hass: HomeAssistant) -> None:
    integration = await async_get_integration(hass, DOMAIN)
    assert integration.integration_type == "device"


async def test_one_device_holds_all_entities(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    device = get_device(hass, entry)
    assert device.name == "Water Softener"
    assert device.manufacturer is None
    assert device.model is None

    entities = er.async_get(hass)
    for entity_id in ENTITY_IDS:
        registered = entities.async_get(entity_id)
        assert registered is not None, entity_id
        assert registered.device_id == device.id


async def test_device_make_and_model(hass: HomeAssistant, entry) -> None:
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_MANUFACTURER: "Harvey", CONF_MODEL: "Dual Flo H20/25"},
    )
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    device = get_device(hass, entry)
    assert device.manufacturer == "Harvey"
    assert device.model == "Dual Flo H20/25"


async def test_old_hardcoded_make_is_cleared(hass: HomeAssistant, entry) -> None:
    """Versions before 1.1.0 labelled every device "Harvey / Generic"."""
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Water Softener",
        manufacturer="Harvey / Generic",
        model="Twin-Tank Metered Softener",
    )
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    device = get_device(hass, entry)
    assert device.manufacturer is None
    assert device.model is None


async def test_existing_entity_ids_are_kept(hass: HomeAssistant, entry) -> None:
    """Upgrading must not rename entities created by earlier versions."""
    entities = er.async_get(hass)
    old = {
        "water_processed": "sensor.my_softener_water_processed_since_refill",
        "salt_level": "sensor.my_softener_salt_level",
        "reset_button": "button.my_softener_reset_salt_level",
    }
    for suffix, entity_id in old.items():
        domain, object_id = entity_id.split(".")
        entities.async_get_or_create(
            domain,
            DOMAIN,
            f"{entry.entry_id}_{suffix}",
            suggested_object_id=object_id,
            config_entry=entry,
        )
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    for entity_id in old.values():
        assert hass.states.get(entity_id) is not None, entity_id


async def test_entity_names_and_classes(hass: HomeAssistant, entry) -> None:
    await set_meter(hass, "1000")
    await setup_entry(hass, entry)

    level = hass.states.get(ENTITY_PREFIX + "salt_level")
    assert level.attributes[ATTR_FRIENDLY_NAME] == "Water Softener Salt level"
    assert level.attributes["state_class"] == SensorStateClass.MEASUREMENT

    remaining = hass.states.get(ENTITY_PREFIX + "salt_remaining")
    assert remaining.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.WEIGHT
    assert remaining.attributes["state_class"] == SensorStateClass.MEASUREMENT

    refill = hass.states.get(ENTITY_PREFIX + "last_refill_date")
    assert refill.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.DATE

    button = hass.states.get(RESET_BUTTON)
    assert button.attributes[ATTR_FRIENDLY_NAME] == "Water Softener Reset salt level"


async def test_removing_entry_deletes_storage_and_issue(
    hass: HomeAssistant, hass_storage, entry: MockConfigEntry
) -> None:
    await set_meter(hass, "5000")
    await setup_entry(hass, entry)
    await hass.services.async_call(
        "button", "press", {"entity_id": RESET_BUTTON}, blocking=True
    )
    await set_meter(hass, "12")  # raise the meter-below-baseline issue
    issue_id = f"meter_below_baseline_{entry.entry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    assert storage_key(entry) in hass_storage

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert storage_key(entry) not in hass_storage
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
