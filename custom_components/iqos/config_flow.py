"""Config flow for IQOS."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DISCOVERY_NAME, CONF_MODEL, DOMAIN
from .protocol import IQOS_CORE_SERVICE_UUID, is_iqos_name, model_from_local_name

SCAN_SECONDS = 12
NEARBY_DEVICE_LIMIT = 12

MENU_MANUAL = "Enter Bluetooth address manually"
MENU_PAIRING_GUIDE = "Check Bluetooth again"
MENU_SEARCH = "Search Bluetooth devices"
MENU_SEARCH_AGAIN = "Search again"
MENU_SELECT_NEARBY = "Select a nearby Bluetooth device"

PAIRING_GUIDE_MENU = {
    "search": MENU_SEARCH,
    "manual": MENU_MANUAL,
}
BLUETOOTH_UNAVAILABLE_MENU = {
    "pairing_guide": MENU_PAIRING_GUIDE,
    "manual": MENU_MANUAL,
}


class IqosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an IQOS config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovery_info: bluetooth.BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, str] = {}
        self._nearby: dict[str, bluetooth.BluetoothServiceInfoBleak] = {}
        self._scan_task: asyncio.Task[None] | None = None

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
        """Show setup choices and pairing instructions."""
        return await self.async_step_pairing_guide()

    async def async_step_pairing_guide(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show setup choices and pairing instructions."""
        if not self._has_connectable_bluetooth():
            return self.async_show_menu(
                step_id="bluetooth_unavailable",
                menu_options=BLUETOOTH_UNAVAILABLE_MENU,
            )

        return self.async_show_menu(
            step_id="pairing_guide",
            menu_options=PAIRING_GUIDE_MENU,
        )

    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Search for nearby IQOS Bluetooth devices."""
        if not self._has_connectable_bluetooth():
            return self.async_show_menu(
                step_id="bluetooth_unavailable",
                menu_options=BLUETOOTH_UNAVAILABLE_MENU,
            )

        if self._scan_task is None:
            self._scan_task = self.hass.async_create_task(self._async_scan_devices())

        if not self._scan_task.done():
            return self.async_show_progress(
                step_id="search",
                progress_action="scan_devices",
                progress_task=self._scan_task,
                description_placeholders={"scan_seconds": str(SCAN_SECONDS)},
            )

        try:
            await self._scan_task
        finally:
            self._scan_task = None

        return self.async_show_progress_done(next_step_id="scan_result")

    async def async_step_scan_result(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show Bluetooth scan results."""
        if self._discovered:
            return await self.async_step_select_device()

        menu_options = {
            "search": MENU_SEARCH_AGAIN,
            "manual": MENU_MANUAL,
        }
        if self._nearby:
            menu_options = {
                "select_nearby": MENU_SELECT_NEARBY,
                **menu_options,
            }

        return self.async_show_menu(
            step_id="scan_result",
            menu_options=menu_options,
            description_placeholders={
                "nearby_devices": self._nearby_device_summary(),
                "scan_seconds": str(SCAN_SECONDS),
            },
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick a discovered IQOS device."""
        if not self._discovered:
            return await self.async_step_search()

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            await self.async_set_unique_id(_normalize_address(address))
            self._abort_if_unique_id_configured()

            name = self._name_for_address(address)
            return self.async_create_entry(
                title=name,
                data=_entry_data(address=address, name=name),
            )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered)}
            ),
            description_placeholders={"count": str(len(self._discovered))},
        )

    async def async_step_select_nearby(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick any nearby Bluetooth device as an IQOS candidate."""
        if not self._nearby:
            return await self.async_step_scan_result()

        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            await self.async_set_unique_id(_normalize_address(address))
            self._abort_if_unique_id_configured()

            name = self._name_for_address(address)
            return self.async_create_entry(
                title=name,
                data=_entry_data(address=address, name=name),
            )

        return self.async_show_form(
            step_id="select_nearby",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._nearby_options())}
            ),
            description_placeholders={"count": str(len(self._nearby))},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup from a Bluetooth address."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip()
            await self.async_set_unique_id(_normalize_address(address))
            self._abort_if_unique_id_configured()

            name = user_input.get(CONF_NAME) or self._name_for_address(address)
            return self.async_create_entry(
                title=name,
                data=_entry_data(address=address, name=name),
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME): str,
                }
            ),
        )

    async def _async_scan_devices(self) -> None:
        """Collect connectable Bluetooth advertisements for a short scan window."""
        self._nearby = {}
        self._discovered = {}
        iqos_found = asyncio.Event()

        @callback
        def _async_discovered_device(
            service_info: bluetooth.BluetoothServiceInfoBleak,
            change: bluetooth.BluetoothChange,
        ) -> None:
            """Record Bluetooth devices seen during this flow."""
            if not service_info.connectable:
                return

            self._record_service_info(service_info)
            if _is_iqos_service_info(service_info):
                iqos_found.set()

        unload = bluetooth.async_register_callback(
            self.hass,
            _async_discovered_device,
            {"connectable": True},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        try:
            try:
                await asyncio.wait_for(iqos_found.wait(), timeout=SCAN_SECONDS)
            except TimeoutError:
                pass
        finally:
            unload()

        self._record_current_service_info()

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
    def _nearby_options(self) -> dict[str, str]:
        """Return nearby Bluetooth devices as address -> label."""
        return {
            service_info.address: _nearby_device_label(service_info)
            for service_info in self._sorted_nearby_devices()
        }

    @callback
    def _nearby_device_summary(self) -> str:
        """Return a short diagnostic list of nearby Bluetooth advertisements."""
        if not self._nearby:
            return "No connectable Bluetooth devices were seen."

        lines = [
            _nearby_device_label(service_info, detailed=True)
            for service_info in self._sorted_nearby_devices()[:NEARBY_DEVICE_LIMIT]
        ]
        if len(self._nearby) > NEARBY_DEVICE_LIMIT:
            lines.append(
                f"- {len(self._nearby) - NEARBY_DEVICE_LIMIT} more device(s) hidden"
            )
        return "\n".join(lines)

    @callback
    def _record_service_info(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Record one Bluetooth advertisement in the current scan result."""
        if not service_info.connectable:
            return

        address = service_info.address
        self._nearby[address] = service_info
        if _is_iqos_service_info(service_info):
            self._discovered[address] = (
                f"{_service_info_name(service_info)} ({address})"
            )

    @callback
    def _record_current_service_info(self) -> None:
        """Merge current Home Assistant Bluetooth discovery cache into results."""
        for service_info in bluetooth.async_discovered_service_info(
            self.hass, connectable=True
        ):
            self._record_service_info(service_info)

    @callback
    def _sorted_nearby_devices(self) -> list[bluetooth.BluetoothServiceInfoBleak]:
        """Return nearby devices with likely IQOS devices first."""
        return sorted(
            self._nearby.values(),
            key=lambda service_info: (
                _is_iqos_service_info(service_info),
                service_info.rssi if service_info.rssi is not None else -999,
                _advertised_name(service_info) or "",
            ),
            reverse=True,
        )

    @callback
    def _has_connectable_bluetooth(self) -> bool:
        """Return true when HA has a connectable Bluetooth scanner/proxy."""
        return bluetooth.async_scanner_count(self.hass, connectable=True) > 0

    @callback
    def _name_for_address(self, address: str) -> str:
        """Find the best name for a manually selected address."""
        service_info = bluetooth.async_last_service_info(
            self.hass, address, connectable=True
        )
        if service_info:
            if _is_iqos_service_info(service_info):
                return _service_info_name(service_info)
            if name := _advertised_name(service_info):
                return f"IQOS {name}"
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
    return _advertised_name(service_info) or f"IQOS {service_info.address}"


@callback
def _advertised_name(service_info: bluetooth.BluetoothServiceInfoBleak) -> str | None:
    """Return the advertised Bluetooth name, if present."""
    return service_info.name or getattr(service_info.device, "name", None)


@callback
def _nearby_device_label(
    service_info: bluetooth.BluetoothServiceInfoBleak, detailed: bool = False
) -> str:
    """Return a diagnostic label for a nearby Bluetooth device."""
    name = _advertised_name(service_info) or "Unnamed"
    iqos_marker = "IQOS match" if _is_iqos_service_info(service_info) else "not matched"
    rssi = service_info.rssi if service_info.rssi is not None else "unknown"
    label = f"{name} ({service_info.address}), RSSI {rssi}, {iqos_marker}"
    if not detailed:
        return label

    service_uuids = ", ".join(service_info.service_uuids[:3]) or "none"
    if len(service_info.service_uuids) > 3:
        service_uuids += f", +{len(service_info.service_uuids) - 3} more"

    manufacturer_ids = ", ".join(
        f"0x{manufacturer_id:04x}"
        for manufacturer_id in service_info.manufacturer_data
    )
    if not manufacturer_ids:
        manufacturer_ids = "none"

    return (
        f"- {label}; services: {service_uuids}; "
        f"manufacturer IDs: {manufacturer_ids}"
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
