"""Sensors for LANCOM Management Cloud."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, CONF_ACCOUNT_ID
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
        stat_key="totalDevices",
    ),
    AccountSensorDescription(
        key="online_devices",
        name="Online Devices",
        icon="mdi:router-wireless",
        stat_key="onlineDevices",
    ),
    AccountSensorDescription(
        key="offline_devices",
        name="Offline Devices",
        icon="mdi:router-wireless-off",
        stat_key="offlineDevices",
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
        device_key="firmwareVersion",
    ),
    DeviceSensorDescription(
        key="device_model",
        name="Model",
        icon="mdi:router",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="type",
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
        device_key="serialNumber",
    ),
    DeviceSensorDescription(
        key="ip_address",
        name="IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_key="ipAddress",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LancomCoordinator = hass.data[DOMAIN][entry.entry_id]
    account_id: str = entry.data[CONF_ACCOUNT_ID]

    entities: list[SensorEntity] = []

    # Account-level sensors
    for desc in ACCOUNT_SENSORS:
        entities.append(LancomAccountSensor(coordinator, account_id, desc))

    # Per-device sensors
    for device_id in coordinator.data["devices"]:
        for desc in DEVICE_SENSORS:
            entities.append(LancomDeviceSensor(coordinator, device_id, desc))

        # WAN sensor if data is available
        entities.append(LancomWanSensor(coordinator, device_id))

    async_add_entities(entities)


class LancomAccountSensor(CoordinatorEntity[LancomCoordinator], SensorEntity):
    """Sensor for account-level statistics."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LancomCoordinator,
        account_id: str,
        description: AccountSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._account_id = account_id
        self._attr_unique_id = f"lmc_{account_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        stats = self.coordinator.data.get("statistics", {})
        return stats.get(self.entity_description.stat_key)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"account_{self._account_id}")},
            name=f"LMC Account {self._account_id}",
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
    def native_value(self) -> Any:
        value = self._device.get(self.entity_description.device_key)
        # Fallback for alternative field names
        if value is None and self.entity_description.device_key == "type":
            value = self._device.get("model") or self._device.get("deviceType")
        if value is None and self.entity_description.device_key == "siteName":
            value = self._device.get("site", {}).get("name") if isinstance(self._device.get("site"), dict) else None
        return value

    @property
    def device_info(self) -> DeviceInfo:
        device = self._device
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.get("name", self._device_id),
            manufacturer=MANUFACTURER,
            model=device.get("type") or device.get("model") or device.get("deviceType"),
            sw_version=device.get("firmwareVersion"),
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

    @property
    def native_value(self) -> str | None:
        wan = self.coordinator.data["wan"].get(self._device_id, {})
        return wan.get("state") or wan.get("status") or wan.get("connectionState")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        wan = self.coordinator.data["wan"].get(self._device_id, {})
        attrs: dict[str, Any] = {}
        for key in ("ipAddress", "gateway", "provider", "type", "rxBytes", "txBytes"):
            if key in wan:
                attrs[key] = wan[key]
        vpn_list = self.coordinator.data["vpn"].get(self._device_id, [])
        attrs["vpn_tunnels"] = len(vpn_list)
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        device = self._device
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device.get("name", self._device_id),
            manufacturer=MANUFACTURER,
            model=device.get("type") or device.get("model"),
            sw_version=device.get("firmwareVersion"),
        )
