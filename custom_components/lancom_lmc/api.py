"""LANCOM Management Cloud API client."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

from .const import DEFAULT_DOMAIN

_LOGGER = logging.getLogger(__name__)


class LancomApiError(Exception):
    """Raised when the API returns an error."""


class LancomAuthError(LancomApiError):
    """Raised when authentication fails."""


class LancomApiClient:
    """Client for the LANCOM Management Cloud API."""

    def __init__(self, api_key: str, account_id: str, session: aiohttp.ClientSession, domain: str = DEFAULT_DOMAIN) -> None:
        self._api_key = api_key
        self._account_id = account_id
        self._session = session
        _base = f"https://{domain.strip().rstrip('/')}"
        self._devices_base          = f"{_base}/cloud-service-devices"
        self._monitoring_base       = f"{_base}/cloud-service-monitoring"
        self._monitor_frontend_base = f"{_base}/cloud-service-monitor-frontend"
        self._config_base           = f"{_base}/cloud-service-config"
        self._auth_base             = f"{_base}/cloud-service-auth"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"LMC-API-KEY {self._api_key}",
            "Accept": "*/*",
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
                if not text.strip():
                    return []
                # Try regular JSON first; fall back to NDJSON (newline-delimited)
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    lines = [l for l in text.strip().splitlines() if l.strip()]
                    return [json.loads(line) for line in lines]
        except aiohttp.ClientError as err:
            raise LancomApiError(f"Connection error: {err}") from err

    async def _post(self, url: str, payload: Any = None) -> Any:
        """Perform a POST request."""
        try:
            kwargs = {"json": payload} if payload is not None else {}
            async with self._session.post(url, headers=self._headers, **kwargs) as resp:
                if resp.status == 401:
                    raise LancomAuthError("Invalid API key or account ID")
                if resp.status == 403:
                    raise LancomAuthError("Access denied")
                if resp.status < 200 or resp.status >= 300:
                    raise LancomApiError(f"API error {resp.status}: {await resp.text()}")
                text = await resp.text()
                if not text.strip():
                    return {}
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {}
        except aiohttp.ClientError as err:
            raise LancomApiError(f"Connection error: {err}") from err

    @staticmethod
    async def get_available_accounts(api_key: str, session: aiohttp.ClientSession, domain: str = DEFAULT_DOMAIN) -> list[dict]:
        """Fetch all accounts accessible with this API key via auth service. Returns list of {id, name, ...}."""
        auth_base = f"https://{domain.strip().rstrip('/')}/cloud-service-auth"
        url = f"{auth_base}/accounts"
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
    async def get_account_name(api_key: str, account_id: str, session: aiohttp.ClientSession, domain: str = DEFAULT_DOMAIN) -> str:
        """Fetch the account display name from the auth service. Falls back to account_id."""
        auth_base = f"https://{domain.strip().rstrip('/')}/cloud-service-auth"
        url = f"{auth_base}/accounts/{account_id}"
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
        url = f"{self._devices_base}/accounts/{self._account_id}/devices"
        result = await self._get(url)
        if isinstance(result, list):
            return result
        # Some API versions return {"devices": [...]}
        return result.get("devices", [result] if isinstance(result, dict) else [])

    async def get_device_config_states(self, device_ids: list[str]) -> dict[str, dict]:
        """Fetch config state for all devices concurrently. Returns {device_id: config_dict}."""
        async def _fetch_one(device_id: str) -> tuple[str, dict]:
            url = f"{self._devices_base}/accounts/{self._account_id}/devices/{device_id}"
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
        url = f"{self._devices_base}/accounts/{self._account_id}/device_statistics"
        return await self._get(url)

    async def get_wan_interfaces(self, device_ids: list[str] | None = None) -> list[dict]:
        """Fetch WAN interface data from monitor-frontend (batched, max 10 per request)."""
        url = f"{self._monitor_frontend_base}/api/{self._account_id}/tables/wan-interface"
        from_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ids = device_ids or []
        batches = [ids[i:i+10] for i in range(0, len(ids), 10)] if ids else [None]
        all_rows: list[dict] = []
        for batch in batches:
            params: dict = {"from": from_ts, "sort": "timeMs", "order": "desc"}
            if batch:
                params["deviceId"] = batch
            try:
                result = await self._get(url, params=params)
                rows = result.get("data", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
                all_rows.extend(rows)
                _LOGGER.debug("WAN batch (%s devices) → %d rows", len(batch) if batch else "all", len(rows))
            except LancomApiError as err:
                _LOGGER.warning("WAN interface data unavailable: %s", err)
        return all_rows

    async def get_wlan_counts(self, device_ids: list[str]) -> dict[str, int]:
        """Fetch connected WLAN client counts per device using the records endpoint."""
        async def _fetch_one(device_id: str) -> tuple[str, int]:
            url = (
                f"{self._monitoring_base}/accounts/{self._account_id}/records/wlan_info_json"
                f"?group=DEVICE&groupId={device_id}&period=MINUTE1&type=json&name=stations&latest=1"
            )
            try:
                data = await self._get(url)
                return device_id, self._parse_wlan_count(data)
            except Exception as err:
                _LOGGER.debug("WLAN count unavailable for %s: %s", device_id, err)
                return device_id, 0

        results = await asyncio.gather(*[_fetch_one(did) for did in device_ids])
        return dict(results)

    @staticmethod
    def _parse_wlan_count(data: Any) -> int:
        """Extract station count from wlan_info_json response.

        Response format:
          {"base": ..., "items": {"stations": {"keys": [...], "values": [[client, ...], ...]}}}
        Empty when no clients: {"base": ..., "items": {}}
        """
        if not isinstance(data, dict):
            return 0
        try:
            vals = data.get("items", {}).get("stations", {}).get("values", [])
            if vals and isinstance(vals[0], list):
                return len(vals[0])
        except (AttributeError, TypeError):
            pass
        return 0

    async def get_vpn_connections(self, device_ids: list[str] | None = None) -> list[dict]:
        """Fetch VPN connection data from monitor-frontend (batched, max 10 per request)."""
        url = f"{self._monitor_frontend_base}/api/{self._account_id}/tables/vpn-connection"
        from_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ids = device_ids or []
        batches = [ids[i:i+10] for i in range(0, len(ids), 10)] if ids else [None]
        all_rows: list[dict] = []
        for batch in batches:
            params: dict = {"from": from_ts}
            if batch:
                params["deviceId"] = batch
            try:
                result = await self._get(url, params=params)
                rows = result.get("data", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
                all_rows.extend(rows)
            except LancomApiError as err:
                _LOGGER.warning("VPN connection data unavailable: %s", err)
        return all_rows

    async def reboot_device(self, device_id: str) -> None:
        """Send reboot command to a device."""
        url = f"{self._devices_base}/accounts/{self._account_id}/actions/reboot"
        await self._post(url, [device_id])

    async def trigger_config_rollout(self, device_id: str) -> None:
        """Trigger a config rollout for a single device via cloud-service-config."""
        url = (
            f"{self._config_base}/configdevice/accounts/{self._account_id}"
            f"/devices/{device_id}/rollout"
            "?forceRollout=false&addDependentCentralSites=false"
        )
        await self._post(url)

    async def trigger_firmware_update(self, device_id: str, beta: bool = False) -> None:
        """Trigger a firmware update for a device.

        With beta=False (default) the stable recommended firmware is used.
        With beta=True the latest available firmware (may be a pre-release) is used.
        """
        fw_url = f"{self._devices_base}/accounts/{self._account_id}/firmware/update"
        firmware_data = await self._get(fw_url, params={"deviceIds": [device_id]})
        device_firmware = firmware_data.get(device_id, {}) if isinstance(firmware_data, dict) else {}
        if beta:
            firmware_id = device_firmware.get("latestId") or device_firmware.get("recommendedId")
        else:
            firmware_id = device_firmware.get("recommendedId")
        if not firmware_id:
            raise LancomApiError(f"No {'beta' if beta else 'stable'} firmware available for device {device_id}")
        await self._post(fw_url, [{"deviceId": device_id, "firmwareId": firmware_id}])

    async def validate(self) -> bool:
        """Validate credentials by fetching device IDs."""
        url = f"{self._devices_base}/accounts/{self._account_id}/devices/ids"
        await self._get(url)
        return True
