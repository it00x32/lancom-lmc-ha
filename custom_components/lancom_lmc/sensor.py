"""Sensors for LANCOM Management Cloud."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, CONF_ACCOUNT_ID, CONF_NAME
from .coordinator import LancomCoordinator


# ── Account-level sensors ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class AccountSensorDescription(SensorEntityDescription):
    stat_key: str = ""


ACCOUNT_SENSORS: tuple[AccountSensorDescription, ...] = (
    AccountSensorDescription(
        key="total_devices",
        name="Total Devices",
        icon="mdi:router-network",
        stat_key="heartbeatState._total",
    ),
    AccountSensorDescription(
        key="online_devices",
        name="Online Devices",
        icon="mdi:router-wireless",
        stat_key="heartbeatState.active",
    ),
    AccountSensorDescription(
        key="offline_devices",
        name="Offline Devices",
        icon="mdi:router-wireless-off",
        stat_key="heartbeatState.inactive",
    ),
    AccountSensorDescription(
        key="active_alerts",
        name="Active Alerts",
        icon="mdi:bell-alert",
        stat_key="alertState.active",
    ),
    AccountSensorDescription(
        key="firmware_outdated",
        name="Firmware Outdated",
        icon="mdi:package-variant-closed-remove",
        stat_key="firmwareState.obsolete",
    ),
    AccountSensorDescription(
        key="config_outdated",
        name="Config Outdated",
        icon="mdi:cog-sync",
        stat_key="configState.outdated",
    ),
)


# ── Per-device sensors ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DeviceSensorDescription(SensorEntityDescription):
    device_key: str = ""


DEVICE_SENSORS: tuple[DeviceSensorDescription, ...] = (
    DeviceSensorDescription(
        key="firmware_version",
        name="Firmware Version",
        icon="mdi:package-up",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="status.fwLabel",
    ),
    DeviceSensorDescription(
        key="device_model",
        name="Model",
        icon="mdi:router",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="status.model",
    ),
    DeviceSensorDescription(
        key="site",
        name="Site",
        icon="mdi:map-marker",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="siteName",
    ),
    DeviceSensorDescription(
        key="serial_number",
        name="Serial Number",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="status.serial",
    ),
    DeviceSensorDescription(
        key="ip_address",
        name="IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="status.ip",
    ),
    DeviceSensorDescription(
        key="firmware_state",
        name="Firmware State",
        icon="mdi:update",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="firmwareState",
    ),
    DeviceSensorDescription(
        key="lifecycle",
        name="Lifecycle",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="status.lifecycle.status",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LancomCoordinator = hass.data[DOMAIN][entry.entry_id]
    account_id: str = entry.data[CONF_ACCOUNT_ID]
    account_name: str = entry.data.get(CONF_NAME) or account_id

    entities: list[SensorEntity] = []

    # Account-level sensors
    for desc in ACCOUNT_SENSORS:
        entities.append(LancomAccountSensor(coordinator, account_id, account_name, desc))
    entities.append(LancomLastSyncSensor(coordinator, account_id, account_name))

    # Per-device sensors
    for device_id, device in coordinator.data["devices"].items():
        for desc in DEVICE_SENSORS:
            entities.append(LancomDeviceSensor(coordinator, device_id, desc))

        entities.append(LancomWanSensor(coordinator, device_id))

        # WLAN client sensor for all devices (routers with built-in WLAN also have clients)
        entities.append(LancomWlanClientSensor(coordinator, device_id))

    async_add_entities(entities)


class LancomAccountSensor(CoordinatorEntity[LancomCoordinator], SensorEntity):
    """Sensor for account-level statistics."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LancomCoordinator,
        account_id: str,
        account_name: str,
        description: AccountSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._account_id = account_id
        self._account_name = account_name
        self._attr_unique_id = f"lmc_{account_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        val = self.coordinator.data.get("statistics", {})
        for key in self.entity_description.stat_key.split("."):
            if not isinstance(val, dict):
                return None
            val = val.get(key)
        return val

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"account_{self._account_id}")},
            name=self._account_name,
            manufacturer=MANUFACTURER,
            model="LANCOM Management Cloud",
        )


class LancomLastSyncSensor(CoordinatorEntity[LancomCoordinator], SensorEntity):
    """Sensor showing the timestamp of the last successful data sync."""

    _attr_has_entity_name = True
    _attr_name = "Last Sync"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LancomCoordinator, account_id: str, account_name: str) -> None:
        super().__init__(coordinator)
        self._account_id = account_id
        self._account_name = account_name
        self._attr_unique_id = f"lmc_{account_id}_last_sync"

    @property
    def native_value(self):
        return self.coordinator.data.get("last_sync")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"account_{self._account_id}")},
            name=self._account_name,
            manufacturer=MANUFACTURER,
            model="LANCOM Management Cloud",
        )


class LancomDeviceSensor(CoordinatorEntity[LancomCoordinator], SensorEntity):
    """Sensor for a specific field of a LANCOM device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LancomCoordinator,
        device_id: str,
        description: DeviceSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def _status(self) -> dict:
        return self._device.get("status", {})

    @property
    def native_value(self) -> Any:
        val = self._device
        for key in self.entity_description.device_key.split("."):
            if not isinstance(val, dict):
                return None
            val = val.get(key)
        return val

    @property
    def device_info(self) -> DeviceInfo:
        status = self._status
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=status.get("name", self._device_id),
            manufacturer=MANUFACTURER,
            model=status.get("model"),
            sw_version=status.get("fwLabel"),
            serial_number=status.get("serial"),
        )


class LancomWanSensor(CoordinatorEntity[LancomCoordinator], SensorEntity):
    """Sensor showing WAN connection status from monitoring API."""

    _attr_has_entity_name = True
    _attr_name = "WAN Status"
    _attr_icon = "mdi:wan"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_wan_status"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    _WAN_STATE_MAP = {
        "ewaninit":          "connected",
        "ewanconnect":       "connected",
        "ewanconnecting":    "connecting",
        "ewandisconnecting": "disconnecting",
        "ewandisconnected":  "disconnected",
        "ewanidle":          "idle",
    }

    @property
    def native_value(self) -> str | None:
        wan = self.coordinator.data["wan"].get(self._device_id, {})
        raw = wan.get("logicalState") or wan.get("state") or wan.get("connectionState")
        if not raw:
            return None
        return self._WAN_STATE_MAP.get(raw.lower().replace("_", ""), raw)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        wan = self.coordinator.data["wan"].get(self._device_id, {})
        attrs: dict[str, Any] = {}
        raw = wan.get("logicalState") or wan.get("state") or wan.get("connectionState")
        if raw:
            attrs["raw_state"] = raw
        for src, dst in (
            ("ipV4", "ip_address"),
            ("ipV4GatewayIp", "gateway"),
            ("connectionType", "connection_type"),
            ("physicalState", "physical_state"),
            ("rxDeltaBytes", "rx_bytes"),
            ("txDeltaBytes", "tx_bytes"),
            ("mobileModemNetwork", "mobile_network"),
            ("mobileModemMode", "mobile_mode"),
            ("mobileModemSignalDecibelMw", "mobile_signal_dbm"),
            ("backupInActiveUse", "backup_active"),
            ("name", "interface_name"),
        ):
            if wan.get(src) is not None:
                attrs[dst] = wan[src]
        vpn_list = self.coordinator.data["vpn"].get(self._device_id, [])
        attrs["vpn_tunnels"] = len(vpn_list)
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        status = self._device.get("status", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=status.get("name", self._device_id),
            manufacturer=MANUFACTURER,
            model=status.get("model"),
            sw_version=status.get("fwLabel"),
            serial_number=status.get("serial"),
        )


class LancomWlanClientSensor(CoordinatorEntity[LancomCoordinator], SensorEntity):
    """Sensor showing the number of connected WLAN clients for an Access Point."""

    _attr_has_entity_name = True
    _attr_name = "WLAN Clients"
    _attr_icon = "mdi:wifi"
    _attr_native_unit_of_measurement = "clients"

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_wlan_clients"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def native_value(self) -> int:
        return self.coordinator.data["wlan_clients"].get(self._device_id, 0)

    @property
    def device_info(self) -> DeviceInfo:
        status = self._device.get("status", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=status.get("name", self._device_id),
            manufacturer=MANUFACTURER,
            model=status.get("model"),
            sw_version=status.get("fwLabel"),
            serial_number=status.get("serial"),
        )
