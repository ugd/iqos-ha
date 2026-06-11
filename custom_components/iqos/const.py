"""Constants for the IQOS integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "iqos"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
]

MANUFACTURER = "Philip Morris International"

CONF_DISCOVERY_NAME = "discovery_name"
CONF_MODEL = "model"

ATTR_ADDRESS = "address"

UPDATE_INTERVAL = timedelta(minutes=15)
CONNECT_TIMEOUT = 20.0
RESPONSE_TIMEOUT = 8.0
STATUS_RESPONSE_TIMEOUT = 0.4
FIND_MY_IQOS_SECONDS = 5.0
