"""LANCOM Management Cloud API client."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import AUTH_BASE, DEVICES_BASE, MONITORING_BASE, USERAGENT_BASE

_LOGGER = logging.getLogger(__name__)


class LancomApiError(Exception):
    """Raised when the API returns an error."""


class LancomAuthError(LancomApiError):
    """Raised when authentication fails."""


class LancomApiClient:
    """Client for the LANCOM Management Cloud API."""

    def __init__(self, api_key: str, account_id: str, session: aiohttp.ClientSession) -> None:
        self._api_key = api_key
        self._account_id = account_id
        self._session = session

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"LMC-API-KEY {self._api_key}",
            "Accept": "application/json",
        }

    async def _get(self, url: str, params: dict | None = None) -> Any:
        """Perform a GET request and handle NDJSON or JSON responses."""
        try:
            async with self._session.get(url, headers=self._headers, params=params) as resp:
                if resp.status == 401:
                    raise LancomAuthError("Invalid API key or account ID")
                if resp.status == 403:
                    raise LancomAuthError("Access denied")
                if resp.status not in (200, 206):
                    raise LancomApiError(f"API error {resp.status}: {await resp.text()}")

                text = await resp.text()
                # Handle newline-delimited JSON (streaming endpoints)
                if "\n" in text.strip():
                    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]
                return json.loads(text)
        except aiohttp.ClientError as err:
            raise LancomApiError(f"Connection error: {err}") from err

    async def _post(self, url: str, payload: Any) -> Any:
        """Perform a POST request."""
        try:
            async with self._session.post(url, headers=self._headers, json=payload) as resp:
                if resp.status == 401:
                    raise LancomAuthError("Invalid API key or account ID")
                if resp.status not in (200, 202):
                    raise LancomApiError(f"API error {resp.status}: {await resp.text()}")
                if resp.content_length:
                    return await resp.json()
                return {}
        except aiohttp.ClientError as err:
            raise LancomApiError(f"Connection error: {err}") from err

    @staticmethod
    async def get_available_accounts(api_key: str, session: aiohttp.ClientSession) -> list[dict]:
        """Fetch all accounts accessible with this API key. Returns list of {id, rights}."""
        url = f"{DEVICES_BASE}/rights/accounts"
        headers = {"Authorization": f"LMC-API-KEY {api_key}", "Accept": "application/json"}
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 401:
                    raise LancomAuthError("Invalid API key")
                if resp.status != 200:
                    raise LancomApiError(f"API error {resp.status}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise LancomApiError(f"Connection error: {err}") from err

    @staticmethod
    async def get_account_name(api_key: str, account_id: str, session: aiohttp.ClientSession) -> str:
        """Fetch the account display name from the auth service. Falls back to account_id."""
        url = f"{AUTH_BASE}/accounts/{account_id}"
        headers = {"Authorization": f"LMC-API-KEY {api_key}", "Accept": "application/json"}
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("name") or account_id
        except Exception:
            pass
        return account_id

    async def get_devices(self) -> list[dict]:
        """Fetch all devices for the account."""
        url = f"{DEVICES_BASE}/accounts/{self._account_id}/devices"
        result = await self._get(url)
        if isinstance(result, list):
            return result
        # Some API versions return {"devices": [...]}
        return result.get("devices", [result] if isinstance(result, dict) else [])

    async def get_device_config_states(self, device_ids: list[str]) -> dict[str, dict]:
        """Fetch config state for all devices concurrently. Returns {device_id: config_dict}."""
        async def _fetch_one(device_id: str) -> tuple[str, dict]:
            url = f"{DEVICES_BASE}/accounts/{self._account_id}/devices/{device_id}"
            try:
                result = await self._get(url)
                return device_id, result.get("config", {})
            except LancomApiError as err:
                _LOGGER.debug("Could not fetch config state for %s: %s", device_id, err)
                return device_id, {}

        results = await asyncio.gather(*[_fetch_one(did) for did in device_ids])
        return dict(results)

    async def get_device_statistics(self) -> dict:
        """Fetch account-level device statistics."""
        url = f"{DEVICES_BASE}/accounts/{self._account_id}/device_statistics"
        return await self._get(url)

    async def get_wan_interfaces(self, device_ids: list[str] | None = None) -> list[dict]:
        """Fetch WAN interface data from monitoring."""
        url = f"{MONITORING_BASE}/api/{self._account_id}/tables/wan-interface"
        params: dict = {}
        if device_ids:
            params["deviceId"] = device_ids[:10]
        try:
            result = await self._get(url, params=params)
            if isinstance(result, dict):
                return result.get("data", [])
            return result if isinstance(result, list) else []
        except LancomApiError as err:
            _LOGGER.debug("WAN interface data unavailable: %s", err)
            return []

    async def get_wlan_stations(self, device_ids: list[str] | None = None) -> list[dict]:
        """Fetch connected WLAN clients from monitoring."""
        url = f"{MONITORING_BASE}/api/{self._account_id}/tables/wlan-station"
        params: dict = {}
        if device_ids:
            params["deviceId"] = device_ids[:10]
        try:
            result = await self._get(url, params=params)
            if isinstance(result, dict):
                return result.get("data", [])
            return result if isinstance(result, list) else []
        except LancomApiError as err:
            _LOGGER.debug("WLAN station data unavailable: %s", err)
            return []

    async def get_vpn_connections(self, device_ids: list[str] | None = None) -> list[dict]:
        """Fetch VPN connection data from monitoring."""
        url = f"{MONITORING_BASE}/api/{self._account_id}/tables/vpn-connection"
        params: dict = {}
        if device_ids:
            params["deviceId"] = device_ids[:10]
        try:
            result = await self._get(url, params=params)
            if isinstance(result, dict):
                return result.get("data", [])
            return result if isinstance(result, list) else []
        except LancomApiError as err:
            _LOGGER.debug("VPN connection data unavailable: %s", err)
            return []

    async def reboot_device(self, device_id: str) -> None:
        """Send reboot command to a device."""
        url = f"{DEVICES_BASE}/accounts/{self._account_id}/actions/reboot"
        await self._post(url, {"deviceIds": [device_id]})

    async def trigger_config_rollout(self, device_id: str) -> None:
        """Trigger a config rollout for a device via the useragent service."""
        url = f"{USERAGENT_BASE}/accounts/{self._account_id}/actions/config-rollout"
        payload = {
            "devices": [{"deviceId": device_id, "orderGroup": 1}],
            "addDependentCentralSites": False,
            "requestTestModeEnabled": False,
        }
        await self._post(url, payload)

    async def trigger_firmware_update(self, device_id: str) -> None:
        """Trigger a firmware update for a device using the recommended firmware version."""
        fw_url = f"{DEVICES_BASE}/accounts/{self._account_id}/firmware/update"
        # Fetch recommended firmware ID for this device
        firmware_data = await self._get(fw_url, params={"deviceIds": [device_id]})
        device_firmware = firmware_data.get(device_id, {}) if isinstance(firmware_data, dict) else {}
        firmware_id = device_firmware.get("recommendedId")
        if not firmware_id:
            raise LancomApiError(f"No recommended firmware available for device {device_id}")
        # Trigger the update
        await self._post(fw_url, [{"deviceId": device_id, "firmwareId": firmware_id}])

    async def validate(self) -> bool:
        """Validate credentials by fetching device IDs."""
        url = f"{DEVICES_BASE}/accounts/{self._account_id}/devices/ids"
        await self._get(url)
        return True
