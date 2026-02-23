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

    def __init__(self) -> None:
        self._api_key: str = ""
        self._accounts: list[dict] = []
        self._update_interval: int = DEFAULT_UPDATE_INTERVAL
        self._name: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Ask for API key and optional settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY].strip()
            self._update_interval = user_input[CONF_UPDATE_INTERVAL]
            self._name = user_input.get(CONF_NAME, "").strip()

            session = async_get_clientsession(self.hass)
            try:
                self._accounts = await LancomApiClient.get_available_accounts(
                    self._api_key, session
                )
            except LancomAuthError:
                errors["base"] = "invalid_auth"
            except LancomApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                if not self._accounts:
                    errors["base"] = "no_accounts"
                elif len(self._accounts) == 1:
                    # Only one account → use it directly
                    return self._create_entry(self._accounts[0]["id"])
                else:
                    # Multiple accounts → let user choose
                    return await self.async_step_select_account()

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
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

    async def async_step_select_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2 (only if multiple accounts): Let user pick an account."""
        if user_input is not None:
            return self._create_entry(user_input[CONF_ACCOUNT_ID])

        account_options = {a["id"]: a["id"] for a in self._accounts}

        schema = vol.Schema(
            {vol.Required(CONF_ACCOUNT_ID): vol.In(account_options)}
        )

        return self.async_show_form(step_id="select_account", data_schema=schema)

    def _create_entry(self, account_id: str) -> ConfigFlowResult:
        name = self._name or account_id
        self.async_set_unique_id(account_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=name,
            data={
                CONF_API_KEY: self._api_key,
                CONF_ACCOUNT_ID: account_id,
                CONF_NAME: name,
            },
            options={
                CONF_UPDATE_INTERVAL: self._update_interval,
            },
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
