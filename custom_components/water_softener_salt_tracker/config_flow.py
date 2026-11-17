"""Config flow for Water Softener Salt Tracker."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CONSUMPTION_RATE,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DEFAULT_CONSUMPTION_RATE,
    DEFAULT_NAME,
    DEFAULT_SALT_CAPACITY,
    DOMAIN,
)
from .coordinator import async_move_baseline_to_meter, read_meter

WATER_METER_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="sensor",
        device_class=[SensorDeviceClass.WATER],
    )
)
SALT_CAPACITY_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=1.0,
        max=100.0,
        step=0.5,
        unit_of_measurement="kg",
        mode=selector.NumberSelectorMode.BOX,
    )
)
CONSUMPTION_RATE_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.05,
        max=5.0,
        step=0.001,
        unit_of_measurement="g/L",
        mode=selector.NumberSelectorMode.BOX,
    )
)
DEVICE_FIELDS = (CONF_MANUFACTURER, CONF_MODEL)


def _device_fields_schema() -> dict[vol.Marker, Any]:
    return {
        vol.Optional(field): selector.TextSelector() for field in DEVICE_FIELDS
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Water Softener Salt Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", DEFAULT_NAME),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Optional("name", default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_WATER_METER_SENSOR): WATER_METER_SELECTOR,
                vol.Required(
                    CONF_SALT_CAPACITY, default=DEFAULT_SALT_CAPACITY
                ): SALT_CAPACITY_SELECTOR,
                vol.Required(
                    CONF_CONSUMPTION_RATE, default=DEFAULT_CONSUMPTION_RATE
                ): CONSUMPTION_RATE_SELECTOR,
                **_device_fields_schema(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Change the water meter, or the softener's make and model."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            new_meter = user_input[CONF_WATER_METER_SENSOR]
            if new_meter != entry.data[CONF_WATER_METER_SENSOR]:
                new_reading = read_meter(self.hass, new_meter)
                if new_reading is None:
                    errors[CONF_WATER_METER_SENSOR] = "meter_unavailable"
                else:
                    await async_move_baseline_to_meter(
                        self.hass, entry, new_meter, new_reading
                    )

            if not errors:
                data = {**entry.data, CONF_WATER_METER_SENSOR: new_meter}
                for field in DEVICE_FIELDS:
                    # A cleared text box is omitted from user_input.
                    if user_input.get(field):
                        data[field] = user_input[field]
                    else:
                        data.pop(field, None)
                return self.async_update_reload_and_abort(entry, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_WATER_METER_SENSOR): WATER_METER_SELECTOR,
                **_device_fields_schema(),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or entry.data
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow changes."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage option values."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SALT_CAPACITY,
                    default=self.config_entry.options.get(
                        CONF_SALT_CAPACITY,
                        self.config_entry.data.get(CONF_SALT_CAPACITY, DEFAULT_SALT_CAPACITY),
                    ),
                ): SALT_CAPACITY_SELECTOR,
                vol.Required(
                    CONF_CONSUMPTION_RATE,
                    default=self.config_entry.options.get(
                        CONF_CONSUMPTION_RATE,
                        self.config_entry.data.get(
                            CONF_CONSUMPTION_RATE, DEFAULT_CONSUMPTION_RATE
                        ),
                    ),
                ): CONSUMPTION_RATE_SELECTOR,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
