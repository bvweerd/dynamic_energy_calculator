# custom_components/dynamic_energy_calculator/config_flow.py

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_CONFIGS,
    CONF_SOURCE_TYPE,
    CONF_SOURCES,
    CONF_PRICE_SENSOR,
    SOURCE_TYPES,
)

STEP_SELECT_SOURCES = "select_sources"
STEP_PRICE_SENSOR = "price_sensor"


class DynamicEnergyCalculatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dynamic Energy Calculator."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self.configs: list[dict] = []
        self.source_type: str | None = None
        self.sources: list[str] | None = None

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Step 1: choose consumption, production, or finish."""
        if user_input is not None:
            choice = user_input[CONF_SOURCE_TYPE]
            if choice == "finish":
                if not self.configs:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._schema_user(),
                        errors={"base": "no_blocks"},
                    )
                return self.async_create_entry(
                    title="Dynamic Energy Calculator",
                    data={CONF_CONFIGS: self.configs},
                )

            # Add a new block
            self.source_type = choice
            return await self.async_step_select_sources()

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema_user(),
        )

    def _schema_user(self) -> vol.Schema:
        """Schema for initial menu."""
        options = [{"value": t, "label": t.title()} for t in SOURCE_TYPES]
        options.append({"value": "finish", "label": "Finish"})

        return vol.Schema(
            {
                vol.Required(CONF_SOURCE_TYPE): selector(
                    {
                        "select": {
                            "options": options,
                            "mode": "dropdown",
                            "custom_value": False,
                        }
                    }
                )
            }
        )

    async def async_step_select_sources(
        self, user_input: dict[str, list[str]] | None = None
    ) -> FlowResult:
        """Step 2: pick one or more kWh meters for this block."""
        if user_input is not None:
            self.sources = user_input[CONF_SOURCES]
            return await self.async_step_price_sensor()

        return self.async_show_form(
            step_id=STEP_SELECT_SOURCES,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCES): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "multiple": True,
                                "device_class": "energy",
                            }
                        }
                    )
                }
            ),
        )

    async def async_step_price_sensor(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Step 3: pick the €/kWh price sensor for this block."""
        if user_input is not None:
            # Save this block
            self.configs.append(
                {
                    CONF_SOURCE_TYPE: self.source_type,
                    CONF_SOURCES: self.sources,
                    CONF_PRICE_SENSOR: user_input[CONF_PRICE_SENSOR],
                }
            )
            # Loop back to add another block or finish
            return await self.async_step_user()

        return self.async_show_form(
            step_id=STEP_PRICE_SENSOR,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PRICE_SENSOR): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "device_class": "monetary",
                            }
                        }
                    )
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> type[config_entries.OptionsFlow]:
        """Allow updating options later."""
        return DynamicEnergyCalculatorOptionsFlowHandler


class DynamicEnergyCalculatorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle updates to a config entry (options)."""

    def __init__(self, config_entry):
        """Initialize options flow state."""
        self.config_entry = config_entry
        self.configs = list(config_entry.data.get(CONF_CONFIGS, []))
        self.source_type: str | None = None
        self.sources: list[str] | None = None

    async def async_step_init(self, user_input=None):
        """Redirect to the same initial menu."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Step 1 under options: choose consumption, production, or finish."""
        if user_input and CONF_SOURCE_TYPE in user_input:
            choice = user_input[CONF_SOURCE_TYPE]
            if choice == "finish":
                if not self.configs:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._schema_user(),
                        errors={"base": "no_blocks"},
                    )
                return self.async_create_entry(
                    title="",
                    data={CONF_CONFIGS: self.configs},
                )
            self.source_type = choice
            return await self.async_step_select_sources()

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema_user(),
        )

    def _schema_user(self) -> vol.Schema:
        """Schema for initial menu under options."""
        options = [{"value": t, "label": t.title()} for t in SOURCE_TYPES]
        options.append({"value": "finish", "label": "Finish"})

        return vol.Schema(
            {
                vol.Required(CONF_SOURCE_TYPE): selector(
                    {
                        "select": {
                            "options": options,
                            "mode": "dropdown",
                            "custom_value": False,
                        }
                    }
                )
            }
        )

    async def async_step_select_sources(self, user_input=None):
        """Step 2 under options: pick kWh meters for this block."""
        if user_input and CONF_SOURCES in user_input:
            self.sources = user_input[CONF_SOURCES]
            return await self.async_step_price_sensor()

        # Pre-fill last block for this type, if any
        default = next(
            (
                block[CONF_SOURCES]
                for block in reversed(self.configs)
                if block[CONF_SOURCE_TYPE] == self.source_type
            ),
            None,
        )

        return self.async_show_form(
            step_id=STEP_SELECT_SOURCES,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SOURCES, default=default): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "multiple": True,
                                "device_class": "energy",
                            }
                        }
                    )
                }
            ),
        )

    async def async_step_price_sensor(self, user_input=None):
        """Step 3 under options: pick €/kWh price sensor for this block."""
        if user_input and CONF_PRICE_SENSOR in user_input:
            self.configs.append(
                {
                    CONF_SOURCE_TYPE: self.source_type,
                    CONF_SOURCES: self.sources,
                    CONF_PRICE_SENSOR: user_input[CONF_PRICE_SENSOR],
                }
            )
            return await self.async_step_user()

        default = next(
            (
                block[CONF_PRICE_SENSOR]
                for block in reversed(self.configs)
                if block[CONF_SOURCE_TYPE] == self.source_type
            ),
            None,
        )

        return self.async_show_form(
            step_id=STEP_PRICE_SENSOR,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PRICE_SENSOR, default=default): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "device_class": "monetary",
                            }
                        }
                    )
                }
            ),
        )
