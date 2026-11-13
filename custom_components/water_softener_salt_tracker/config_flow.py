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
    CONF_SALT_CAPACITY,
    CONF_WATER_METER_SENSOR,
    DEFAULT_CONSUMPTION_RATE,
    DEFAULT_NAME,
    DEFAULT_SALT_CAPACITY,
    DOMAIN,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Water Softener Salt Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get("name", DEFAULT_NAME),
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Optional("name", default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_WATER_METER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        device_class=[SensorDeviceClass.WATER],
                    )
                ),
                vol.Required(
                    CONF_SALT_CAPACITY, default=DEFAULT_SALT_CAPACITY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0, max=100.0, step=0.5, unit_of_measurement="kg"
                    )
                ),
                vol.Required(
                    CONF_CONSUMPTION_RATE, default=DEFAULT_CONSUMPTION_RATE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.05, max=5.0, step=0.005, unit_of_measurement="g/L"
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
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
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0, max=100.0, step=0.5, unit_of_measurement="kg"
                    )
                ),
                vol.Required(
                    CONF_CONSUMPTION_RATE,
                    default=self.config_entry.options.get(
                        CONF_CONSUMPTION_RATE,
                        self.config_entry.data.get(
                            CONF_CONSUMPTION_RATE, DEFAULT_CONSUMPTION_RATE
                        ),
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.05, max=5.0, step=0.005, unit_of_measurement="g/L"
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
