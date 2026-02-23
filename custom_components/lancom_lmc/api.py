"""LANCOM Management Cloud API client."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import DEVICES_BASE, MONITORING_BASE, USERAGENT_BASE, AUTH_BASE

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

    async def _post(self, url: str, payload: dict) -> Any:
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

    async def get_account_name(self) -> str:
        """Fetch the account name from the auth service."""
        url = f"{AUTH_BASE}/accounts/{self._account_id}"
        try:
            result = await self._get(url)
            return result.get("name", self._account_id)
        except LancomApiError as err:
            _LOGGER.debug("Could not fetch account name: %s", err)
            return self._account_id

    async def get_devices(self) -> list[dict]:
        """Fetch all devices for the account."""
        url = f"{DEVICES_BASE}/accounts/{self._account_id}/devices"
        result = await self._get(url)
        if isinstance(result, list):
            return result
        # Some API versions return {"devices": [...]}
        return result.get("devices", [result] if isinstance(result, dict) else [])

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

    async def trigger_firmware_update(self, device_id: str) -> None:
        """Trigger a firmware update for a device via the useragent service."""
        url = f"{USERAGENT_BASE}/accounts/{self._account_id}/actions/firmware-update"
        await self._post(url, {"deviceIds": [device_id]})

    async def validate(self) -> bool:
        """Validate credentials by fetching device IDs."""
        url = f"{DEVICES_BASE}/accounts/{self._account_id}/devices/ids"
        await self._get(url)
        return True
