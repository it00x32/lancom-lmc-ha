"""Config flow for LANCOM Management Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LancomApiClient, LancomAuthError, LancomApiError
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_ACCOUNT_ID,
    CONF_UPDATE_INTERVAL,
    CONF_NAME,
    DEFAULT_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class LancomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for LANCOM Management Cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            account_id = user_input[CONF_ACCOUNT_ID].strip()
            account_name = user_input.get(CONF_NAME, "").strip() or account_id
            update_interval = user_input[CONF_UPDATE_INTERVAL]

            await self.async_set_unique_id(account_id)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = LancomApiClient(api_key, account_id, session)

            try:
                await client.validate()
            except LancomAuthError:
                errors["base"] = "invalid_auth"
            except LancomApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=account_name,
                    data={
                        CONF_API_KEY: api_key,
                        CONF_ACCOUNT_ID: account_id,
                        CONF_NAME: account_name,
                    },
                    options={
                        CONF_UPDATE_INTERVAL: update_interval,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_ACCOUNT_ID): str,
                vol.Optional(CONF_NAME): str,
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(int, vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LancomOptionsFlow()


class LancomOptionsFlow(OptionsFlow):
    """Handle options (Einstellungen nachträglich ändern)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current_interval): vol.All(
                    int, vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
