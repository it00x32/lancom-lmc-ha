"""Binary sensors for LANCOM Management Cloud."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
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
    async_add_entities(
        LancomDeviceOnlineSensor(coordinator, device_id)
        for device_id in coordinator.data["devices"]
    )


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
