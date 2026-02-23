"""Binary sensors for LANCOM Management Cloud."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LancomCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LancomCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id in coordinator.data["devices"]:
        entities.append(LancomDeviceOnlineSensor(coordinator, device_id))
        entities.append(LancomDeviceAlertSensor(coordinator, device_id))
        entities.append(LancomFirmwareOutdatedSensor(coordinator, device_id))
        entities.append(LancomConfigOutdatedSensor(coordinator, device_id))
    async_add_entities(entities)


class LancomDeviceOnlineSensor(CoordinatorEntity[LancomCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether a LANCOM device is online."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    _attr_name = "Online"

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_online"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def _status(self) -> dict:
        return self._device.get("status", {})

    @property
    def is_on(self) -> bool:
        return self._status.get("heartbeatState", "").upper() == "ACTIVE"

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


class LancomDeviceAlertSensor(CoordinatorEntity[LancomCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether a LANCOM device has an active alert."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_name = "Alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_alert"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def is_on(self) -> bool:
        return self._device.get("alerting", {}).get("hasAlert", False)

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


class LancomFirmwareOutdatedSensor(CoordinatorEntity[LancomCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether a device's firmware is outdated."""

    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_has_entity_name = True
    _attr_name = "Firmware Update Available"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_firmware_outdated"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def is_on(self) -> bool:
        return self._device.get("firmwareState", "").upper() == "OBSOLETE"

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


class LancomConfigOutdatedSensor(CoordinatorEntity[LancomCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether a device's config is outdated."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_name = "Config Outdated"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_config_outdated"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def is_on(self) -> bool:
        config = self.coordinator.data["config_states"].get(self._device_id, {})
        return config.get("category", "").upper() == "OUTDATED"

    @property
    def extra_state_attributes(self) -> dict:
        config = self.coordinator.data["config_states"].get(self._device_id, {})
        return {"config_state": config.get("state")} if config.get("state") else {}

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
