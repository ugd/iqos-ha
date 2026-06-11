"""Shared IQOS entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import IqosCoordinator
from .protocol import DeviceModel


class IqosEntity(CoordinatorEntity[IqosCoordinator]):
    """Base class for IQOS entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: IqosCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}".lower()

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device information."""
        data = self.coordinator.data
        model = data.model.display_name if data else None
        if model is None:
            model = DeviceModel.UNKNOWN.display_name

        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, self.coordinator.address)},
            name=self.coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=model,
            serial_number=data.device_info.serial_number if data else None,
            sw_version=data.stick_firmware if data else None,
        )

