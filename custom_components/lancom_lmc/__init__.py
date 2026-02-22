"""LANCOM Management Cloud integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LancomApiClient
from .const import DOMAIN, CONF_API_KEY, CONF_ACCOUNT_ID
from .coordinator import LancomCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LANCOM Management Cloud from a config entry."""
    session = async_get_clientsession(hass)
    client = LancomApiClient(
        api_key=entry.data[CONF_API_KEY],
        account_id=entry.data[CONF_ACCOUNT_ID],
        session=session,
    )

    coordinator = LancomCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_reboot(call: ServiceCall) -> None:
        device_id = call.data.get("device_id")
        if device_id:
            await client.reboot_device(device_id)
            _LOGGER.info("Reboot command sent to device %s", device_id)

    hass.services.async_register(DOMAIN, "reboot_device", handle_reboot)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
