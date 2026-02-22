"""Config flow for LANCOM Management Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LancomApiClient, LancomAuthError, LancomApiError
from .const import DOMAIN, CONF_API_KEY, CONF_ACCOUNT_ID

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_ACCOUNT_ID): str,
    }
)


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
                    title=f"LMC ({account_id})",
                    data={
                        CONF_API_KEY: api_key,
                        CONF_ACCOUNT_ID: account_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
