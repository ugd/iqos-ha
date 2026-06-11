"""IQOS integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import IqosCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IQOS from a config entry."""
    _LOGGER.debug(
        "Setting up IQOS entry %s for address %s",
        entry.entry_id,
        entry.data.get(CONF_ADDRESS),
    )
    coordinator = IqosCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Finished setting up IQOS entry %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an IQOS config entry."""
    _LOGGER.debug("Unloading IQOS entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Unloaded IQOS entry %s", entry.entry_id)
    return unload_ok
