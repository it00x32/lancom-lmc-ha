"""Data update coordinator for LANCOM Management Cloud."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LancomApiClient, LancomApiError
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class LancomCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches all LMC data periodically."""

    def __init__(self, hass: HomeAssistant, client: LancomApiClient, update_interval_minutes: int, beta_firmware: bool = False) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client
        self.beta_firmware = beta_firmware

    async def _async_update_data(self) -> dict:
        """Fetch all data from the LMC API."""
        try:
            devices = await self.client.get_devices()
            statistics = await self.client.get_device_statistics()

            device_ids = [d["id"] for d in devices if "id" in d]
            wan_data, vpn_data, wlan_clients_by_device, config_states = await asyncio.gather(
                self.client.get_wan_interfaces(device_ids),
                self.client.get_vpn_connections(device_ids[:10]),
                self.client.get_wlan_counts(device_ids),
                self.client.get_device_config_states(device_ids),
            )

            # Index WAN data by deviceId – prefer active/primary interface, then most recent
            wan_by_device: dict[str, dict] = {}
            for entry in wan_data:
                did = entry.get("deviceId")
                if not did:
                    continue
                existing = wan_by_device.get(did)
                if existing is None:
                    wan_by_device[did] = entry
                else:
                    # Prefer entry with an active logicalState over a disconnected one
                    state = (entry.get("logicalState") or "").lower()
                    existing_state = (existing.get("logicalState") or "").lower()
                    is_active = "disconnect" not in state and "idle" not in state and state != ""
                    existing_active = "disconnect" not in existing_state and "idle" not in existing_state and existing_state != ""
                    if is_active and not existing_active:
                        wan_by_device[did] = entry

            vpn_by_device: dict[str, list] = {}
            for entry in vpn_data:
                did = entry.get("deviceId")
                if did:
                    vpn_by_device.setdefault(did, []).append(entry)

            return {
                "devices": {d["id"]: d for d in devices if "id" in d},
                "statistics": statistics,
                "last_sync": datetime.now(timezone.utc),
                "config_states": config_states,
                "wan": wan_by_device,
                "vpn": vpn_by_device,
                "wlan_clients": wlan_clients_by_device,
            }
        except LancomApiError as err:
            raise UpdateFailed(f"LMC API error: {err}") from err
