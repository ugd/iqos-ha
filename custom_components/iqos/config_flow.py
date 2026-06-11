"""Config flow for IQOS."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DISCOVERY_NAME, CONF_MODEL, DOMAIN
from .protocol import IQOS_CORE_SERVICE_UUID, is_iqos_name, model_from_local_name


class IqosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an IQOS config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovery_info: bluetooth.BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle a Bluetooth discovery."""
        if not _is_iqos_service_info(discovery_info):
            return self.async_abort(reason="not_supported")

        self._discovery_info = discovery_info
        await self.async_set_unique_id(_normalize_address(discovery_info.address))
        self._abort_if_unique_id_configured(
            updates={
                CONF_ADDRESS: discovery_info.address,
                CONF_DISCOVERY_NAME: _service_info_name(discovery_info),
            }
        )
        self.context["title_placeholders"] = {
            CONF_NAME: _service_info_name(discovery_info)
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm Bluetooth discovery."""
        if self._discovery_info is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            return self._create_entry_from_service_info(self._discovery_info)

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                CONF_NAME: _service_info_name(self._discovery_info),
                CONF_ADDRESS: self._discovery_info.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup from the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            await self.async_set_unique_id(_normalize_address(address))
            self._abort_if_unique_id_configured()

            name = user_input.get(CONF_NAME) or self._name_for_address(address)
            return self.async_create_entry(
                title=name,
                data=_entry_data(address=address, name=name),
            )

        await bluetooth.async_request_active_scan(self.hass)
        options = self._discovered_options()
        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(options) if options else str,
                vol.Optional(CONF_NAME): str,
            }
        )
        if not options:
            errors["base"] = "no_devices_found"

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @callback
    def _discovered_options(self) -> dict[str, str]:
        """Return currently discovered IQOS devices as address -> label."""
        options: dict[str, str] = {}
        for service_info in bluetooth.async_discovered_service_info(
            self.hass, connectable=True
        ):
            if not _is_iqos_service_info(service_info):
                continue
            address = service_info.address
            options[address] = f"{_service_info_name(service_info)} ({address})"
        return options

    @callback
    def _name_for_address(self, address: str) -> str:
        """Find the best name for a manually selected address."""
        service_info = bluetooth.async_last_service_info(
            self.hass, address, connectable=True
        )
        if service_info and _is_iqos_service_info(service_info):
            return _service_info_name(service_info)
        return f"IQOS {address}"

    @callback
    def _create_entry_from_service_info(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Create a config entry from Bluetooth service info."""
        name = _service_info_name(service_info)
        return self.async_create_entry(
            title=name,
            data=_entry_data(address=service_info.address, name=name),
        )


@callback
def _entry_data(address: str, name: str) -> dict[str, str]:
    """Build config entry data."""
    model = model_from_local_name(name)
    data = {
        CONF_ADDRESS: address,
        CONF_NAME: name,
        CONF_DISCOVERY_NAME: name,
    }
    if model.value:
        data[CONF_MODEL] = model.value
    return data


@callback
def _service_info_name(service_info: bluetooth.BluetoothServiceInfoBleak) -> str:
    """Return the best display name from service info."""
    return (
        service_info.name
        or getattr(service_info.device, "name", None)
        or f"IQOS {service_info.address}"
    )


@callback
def _is_iqos_service_info(service_info: bluetooth.BluetoothServiceInfoBleak) -> bool:
    """Return true if service info appears to describe an IQOS device."""
    service_uuids = {uuid.lower() for uuid in service_info.service_uuids}
    return IQOS_CORE_SERVICE_UUID in service_uuids or is_iqos_name(
        _service_info_name(service_info)
    )


@callback
def _normalize_address(address: str) -> str:
    """Normalize a Bluetooth address for config-entry unique IDs."""
    return address.upper()

