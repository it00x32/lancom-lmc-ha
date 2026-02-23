"""Buttons for LANCOM Management Cloud."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import LancomCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LancomCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id in coordinator.data["devices"]:
        entities.append(LancomRebootButton(coordinator, device_id))
        entities.append(LancomFirmwareUpdateButton(coordinator, device_id))
        entities.append(LancomConfigRolloutButton(coordinator, device_id))
    async_add_entities(entities)


class LancomRebootButton(CoordinatorEntity[LancomCoordinator], ButtonEntity):
    """Button to reboot a LANCOM device."""

    _attr_has_entity_name = True
    _attr_name = "Reboot"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_reboot"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    async def async_press(self) -> None:
        """Send reboot command to this device."""
        await self.coordinator.client.reboot_device(self._device_id)
        _LOGGER.info("Reboot command sent to device %s", self._device_id)

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


class LancomFirmwareUpdateButton(CoordinatorEntity[LancomCoordinator], ButtonEntity):
    """Button to trigger a firmware update on a LANCOM device."""

    _attr_has_entity_name = True
    _attr_name = "Firmware Update"
    _attr_icon = "mdi:package-up"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_firmware_update"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    async def async_press(self) -> None:
        """Trigger firmware update for this device."""
        await self.coordinator.client.trigger_firmware_update(self._device_id)
        _LOGGER.info("Firmware update triggered for device %s", self._device_id)

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


class LancomConfigRolloutButton(CoordinatorEntity[LancomCoordinator], ButtonEntity):
    """Button to trigger a config rollout on a LANCOM device."""

    _attr_has_entity_name = True
    _attr_name = "Config Rollout"
    _attr_icon = "mdi:cog-sync"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LancomCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_config_rollout"

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    async def async_press(self) -> None:
        """Trigger config rollout for this device."""
        await self.coordinator.client.trigger_config_rollout(self._device_id)
        _LOGGER.info("Config rollout triggered for device %s", self._device_id)

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
