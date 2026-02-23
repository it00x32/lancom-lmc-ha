"""Data update coordinator for LANCOM Management Cloud."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LancomApiClient, LancomApiError
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class LancomCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches all LMC data periodically."""

    def __init__(self, hass: HomeAssistant, client: LancomApiClient, update_interval_minutes: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        """Fetch all data from the LMC API."""
        try:
            devices = await self.client.get_devices()
            statistics = await self.client.get_device_statistics()
            account_name = await self.client.get_account_name()

            device_ids = [d["id"] for d in devices if "id" in d]
            wan_data = await self.client.get_wan_interfaces(device_ids[:10])
            vpn_data = await self.client.get_vpn_connections(device_ids[:10])
            wlan_data = await self.client.get_wlan_stations(device_ids[:10])

            # Index monitoring data by deviceId for quick lookup
            wan_by_device: dict[str, dict] = {}
            for entry in wan_data:
                did = entry.get("deviceId")
                if did:
                    wan_by_device.setdefault(did, entry)

            vpn_by_device: dict[str, list] = {}
            for entry in vpn_data:
                did = entry.get("deviceId")
                if did:
                    vpn_by_device.setdefault(did, []).append(entry)

            wlan_clients_by_device: dict[str, int] = {}
            for entry in wlan_data:
                did = entry.get("deviceId")
                if did:
                    wlan_clients_by_device[did] = wlan_clients_by_device.get(did, 0) + 1

            return {
                "devices": {d["id"]: d for d in devices if "id" in d},
                "statistics": statistics,
                "account_name": account_name,
                "wan": wan_by_device,
                "vpn": vpn_by_device,
                "wlan_clients": wlan_clients_by_device,
            }
        except LancomApiError as err:
            raise UpdateFailed(f"LMC API error: {err}") from err
