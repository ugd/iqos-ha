"""Coordinator for IQOS devices."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_DISCOVERY_NAME, DOMAIN, UPDATE_INTERVAL
from .device import IqosData, IqosDeviceClient, IqosError

_LOGGER = logging.getLogger(__name__)


class IqosCoordinator(DataUpdateCoordinator[IqosData]):
    """DataUpdateCoordinator for one configured IQOS device."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        address = entry.data[CONF_ADDRESS]
        name = (
            entry.data.get(CONF_NAME)
            or entry.data.get(CONF_DISCOVERY_NAME)
            or f"IQOS {address}"
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}-{address}",
            update_interval=UPDATE_INTERVAL,
        )
        self.address = address
        self.client = IqosDeviceClient(hass, address, name)

    @property
    def device_name(self) -> str:
        """Return current or configured device name."""
        if self.data:
            return self.data.name
        return self.client.name

    async def _async_update_data(self) -> IqosData:
        """Fetch data from the IQOS device."""
        try:
            return await self.client.async_read_data()
        except IqosError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected IQOS update failure: {err}") from err

    async def async_set_brightness(self, level: str) -> None:
        """Set brightness then refresh state."""
        await self.client.async_set_brightness(level)
        await self.async_request_refresh()

    async def async_set_flexpuff(self, enabled: bool) -> None:
        """Set FlexPuff then refresh state."""
        await self.client.async_set_flexpuff(enabled)
        await self.async_request_refresh()

    async def async_set_flexbattery_mode(self, mode: str) -> None:
        """Set FlexBattery mode then refresh state."""
        await self.client.async_set_flexbattery_mode(mode)
        await self.async_request_refresh()

    async def async_set_pause_mode(self, enabled: bool) -> None:
        """Set Pause Mode then refresh state."""
        await self.client.async_set_pause_mode(enabled)
        await self.async_request_refresh()

    async def async_set_autostart(self, enabled: bool) -> None:
        """Set Auto Start then refresh state."""
        await self.client.async_set_autostart(enabled)
        await self.async_request_refresh()

    async def async_set_smartgesture(self, enabled: bool) -> None:
        """Set Smart Gesture then refresh state."""
        await self.client.async_set_smartgesture(enabled)
        await self.async_request_refresh()

    async def async_set_vibration_setting(self, key: str, enabled: bool) -> None:
        """Set one vibration setting then refresh state."""
        if self.data is None:
            raise UpdateFailed("Cannot update IQOS vibration setting before data is loaded")
        await self.client.async_set_vibration_setting(self.data, key, enabled)
        await self.async_request_refresh()

    async def async_find_my_iqos(self) -> None:
        """Run Find My IQOS."""
        await self.client.async_find_my_iqos()

    async def async_lock(self) -> None:
        """Lock the device."""
        await self.client.async_lock()
        await self.async_request_refresh()

    async def async_unlock(self) -> None:
        """Unlock the device."""
        await self.client.async_unlock()
        await self.async_request_refresh()
