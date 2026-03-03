"""LANCOM Management Cloud integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LancomApiClient
from .const import DOMAIN, CONF_API_KEY, CONF_ACCOUNT_ID, CONF_UPDATE_INTERVAL, CONF_BETA_FIRMWARE, CONF_DOMAIN, DEFAULT_UPDATE_INTERVAL, DEFAULT_DOMAIN
from .coordinator import LancomCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "button", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LANCOM Management Cloud from a config entry."""
    session = async_get_clientsession(hass)
    client = LancomApiClient(
        api_key=entry.data[CONF_API_KEY],
        account_id=entry.data[CONF_ACCOUNT_ID],
        session=session,
        domain=entry.data.get(CONF_DOMAIN, DEFAULT_DOMAIN),
    )

    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    beta_firmware = entry.options.get(CONF_BETA_FIRMWARE, False)
    coordinator = LancomCoordinator(hass, client, update_interval, beta_firmware)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    async def handle_reboot(call: ServiceCall) -> None:
        device_id = call.data.get("device_id")
        if device_id:
            await client.reboot_device(device_id)
            _LOGGER.info("Reboot command sent to device %s", device_id)

    hass.services.async_register(DOMAIN, "reboot_device", handle_reboot)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
