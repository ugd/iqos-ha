"""BLE device access for IQOS devices."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any, TypeVar

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    CONNECT_TIMEOUT,
    FIND_MY_IQOS_SECONDS,
    RESPONSE_TIMEOUT,
    STATUS_RESPONSE_TIMEOUT,
)
from .protocol import (
    ALL_DIAGNOSIS_COMMANDS,
    AUTOSTART_STATUS_SUBTYPE,
    BATTERY_CHARACTERISTIC_UUID,
    DeviceInfo,
    DeviceModel,
    DiagnosticData,
    FirmwareKind,
    LOAD_AUTOSTART_COMMAND,
    LOAD_BATTERY_VOLTAGE_COMMAND,
    LOAD_BRIGHTNESS_COMMAND,
    LOAD_FLEXBATTERY_COMMAND,
    LOAD_FLEXPUFF_COMMAND,
    LOAD_HOLDER_FIRMWARE_VERSION_COMMAND,
    LOAD_PAUSEMODE_COMMAND,
    LOAD_SMARTGESTURE_COMMAND,
    LOAD_STICK_FIRMWARE_VERSION_COMMAND,
    LOAD_VIBRATE_CHARGE_START_COMMAND,
    LOAD_VIBRATION_SETTINGS_COMMAND,
    LOCK_COMMANDS,
    MANUFACTURER_NAME_CHARACTERISTIC_UUID,
    MODEL_NUMBER_CHARACTERISTIC_UUID,
    ProductNumberKind,
    SCP_CONTROL_CHARACTERISTIC_UUID,
    SERIAL_NUMBER_CHARACTERISTIC_UUID,
    SMARTGESTURE_STATUS_SUBTYPE,
    SOFTWARE_REVISION_CHARACTERISTIC_UUID,
    START_VIBRATE_COMMAND,
    STATUS_CHECKSUM_CANDIDATES,
    STOP_VIBRATE_COMMAND,
    UNLOCK_COMMANDS,
    VibrationSettings,
    autostart_command,
    brightness_commands,
    flexbattery_mode_command,
    flexpuff_command,
    model_from_local_name,
    parse_autostart_response,
    parse_battery_level,
    parse_brightness_response,
    parse_charge_start_vibration_response,
    parse_diagnosis_response,
    parse_firmware_version,
    parse_flexbattery_mode_response,
    parse_flexpuff_response,
    parse_pausemode_response,
    parse_product_number,
    parse_smartgesture_response,
    parse_toggle_status_response,
    parse_vibration_settings_response,
    pausemode_command,
    product_number_command,
    smartgesture_command,
    toggle_status_command,
    vibration_commands,
)

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")
WEAK_RSSI_THRESHOLD = -90


class IqosError(Exception):
    """Base IQOS integration error."""


class IqosConnectionError(IqosError):
    """Raised when a BLE connection cannot be established."""


@dataclass(slots=True)
class IqosData:
    """A complete IQOS state snapshot."""

    address: str
    name: str
    model: DeviceModel
    rssi: int | None
    device_info: DeviceInfo
    battery_level: int | None = None
    battery_voltage: float | None = None
    total_smoking_count: int | None = None
    days_used: int | None = None
    brightness: str | None = None
    flexpuff: bool | None = None
    flexbattery_mode: str | None = None
    pause_mode: bool | None = None
    autostart: bool | None = None
    smartgesture: bool | None = None
    vibration_heating_start: bool | None = None
    vibration_starting_to_use: bool | None = None
    vibration_puff_end: bool | None = None
    vibration_manually_terminated: bool | None = None
    vibration_charging_start: bool | None = None
    product_number: str | None = None
    holder_product_number: str | None = None
    stick_firmware: str | None = None
    holder_firmware: str | None = None


class IqosBleSession:
    """Short-lived Bleak session for one IQOS device."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        """Initialize the session."""
        self._hass = hass
        self._address = address
        self._name = name
        self._client: BleakClientWithServiceCache | None = None
        self._notification_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._request_lock = asyncio.Lock()

    async def __aenter__(self) -> IqosBleSession:
        """Connect and subscribe to IQOS SCP notifications."""
        ble_device = self._ble_device()
        if ble_device is None:
            _LOGGER.warning(
                "IQOS %s (%s) is not reachable by a connectable Bluetooth adapter",
                self._name,
                self._address,
            )
            raise IqosConnectionError(
                f"{self._name} is not reachable by a connectable adapter"
            )

        self._log_last_service_info("Connecting to")
        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self._name,
                self._disconnected,
                ble_device_callback=self._ble_device,
                timeout=CONNECT_TIMEOUT,
            )
        except Exception as err:
            _LOGGER.warning(
                "Failed to connect to IQOS %s (%s): %s",
                self._name,
                self._address,
                err,
                exc_info=True,
            )
            raise IqosConnectionError(
                f"failed to connect to {self._name}: {err}"
            ) from err

        _LOGGER.debug("Connected to IQOS %s (%s)", self._name, self._address)
        try:
            await self._client.start_notify(
                SCP_CONTROL_CHARACTERISTIC_UUID, self._notification
            )
        except Exception as err:
            _LOGGER.warning(
                "Connected to IQOS %s (%s), but failed to start notifications: %s",
                self._name,
                self._address,
                err,
                exc_info=True,
            )
            await self._client.disconnect()
            self._client = None
            raise IqosConnectionError(
                f"failed to subscribe to IQOS notifications for {self._name}: {err}"
            ) from err

        _LOGGER.debug(
            "Subscribed to IQOS notifications for %s (%s)",
            self._name,
            self._address,
        )
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Unsubscribe and disconnect."""
        client = self._client
        if client is None:
            return
        try:
            await client.stop_notify(SCP_CONTROL_CHARACTERISTIC_UUID)
        except Exception as err:  # noqa: BLE cleanup should not mask the real error.
            _LOGGER.debug(
                "Failed to stop IQOS notifications for %s: %s",
                self._name,
                err,
            )
        finally:
            try:
                await client.disconnect()
            except Exception as err:  # noqa: BLE cleanup should not mask real error.
                _LOGGER.debug("Failed to disconnect IQOS %s: %s", self._name, err)
            self._client = None
            _LOGGER.debug("Disconnected from IQOS %s (%s)", self._name, self._address)

    def _ble_device(self) -> Any | None:
        """Return the currently reachable connectable BLE device."""
        return bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )

    def _disconnected(self, _client: BleakClientWithServiceCache) -> None:
        """Handle unexpected disconnection."""
        self._client = None
        _LOGGER.debug("IQOS %s (%s) disconnected", self._name, self._address)

    def _notification(self, _sender: Any, data: bytearray) -> None:
        """Queue an SCP notification frame."""
        payload = bytes(data)
        _LOGGER.debug(
            "IQOS %s (%s) notification: %s",
            self._name,
            self._address,
            payload.hex(" "),
        )
        self._notification_queue.put_nowait(payload)

    @property
    def client(self) -> BleakClientWithServiceCache:
        """Return the connected Bleak client."""
        if self._client is None:
            raise IqosConnectionError(f"{self._name} is not connected")
        return self._client

    async def read_battery_level(self) -> int:
        """Read battery level from the IQOS GATT characteristic."""
        _LOGGER.debug(
            "Reading IQOS battery level for %s (%s)",
            self._name,
            self._address,
        )
        return parse_battery_level(
            bytes(await self.client.read_gatt_char(BATTERY_CHARACTERISTIC_UUID))
        )

    async def read_device_info(self) -> DeviceInfo:
        """Read standard BLE Device Information characteristics."""
        _LOGGER.debug(
            "Reading IQOS device information for %s (%s)",
            self._name,
            self._address,
        )
        return DeviceInfo(
            model_number=await self._read_text(MODEL_NUMBER_CHARACTERISTIC_UUID),
            serial_number=await self._read_text(SERIAL_NUMBER_CHARACTERISTIC_UUID),
            software_revision=await self._read_text(
                SOFTWARE_REVISION_CHARACTERISTIC_UUID
            ),
            manufacturer_name=await self._read_text(
                MANUFACTURER_NAME_CHARACTERISTIC_UUID
            ),
        )

    async def _read_text(self, characteristic_uuid: str) -> str | None:
        """Read and decode an optional GATT text characteristic."""
        try:
            value = await self.client.read_gatt_char(characteristic_uuid)
        except Exception as err:
            _LOGGER.debug(
                "Could not read IQOS characteristic %s from %s: %s",
                characteristic_uuid,
                self._name,
                err,
            )
            return None
        return bytes(value).decode(errors="replace").strip("\x00") or None

    async def send(self, command: bytes) -> None:
        """Send an IQOS command that does not require a response frame."""
        _LOGGER.debug(
            "IQOS %s (%s) write: %s",
            self._name,
            self._address,
            command.hex(" "),
        )
        await self.client.write_gatt_char(
            SCP_CONTROL_CHARACTERISTIC_UUID, command, response=True
        )

    async def request(self, command: bytes, timeout: float = RESPONSE_TIMEOUT) -> bytes:
        """Send an IQOS command and wait for the next response notification."""
        async with self._request_lock:
            self._drain_notifications()
            await self.send(command)
            try:
                response = await asyncio.wait_for(
                    self._notification_queue.get(), timeout
                )
                _LOGGER.debug(
                    "IQOS %s (%s) response: %s",
                    self._name,
                    self._address,
                    response.hex(" "),
                )
                return response
            except TimeoutError as err:
                _LOGGER.warning(
                    "No IQOS response notification received for %s (%s) after %.1fs",
                    self._name,
                    self._address,
                    timeout,
                )
                raise IqosConnectionError(
                    f"no IQOS response notification received for {self._name}"
                ) from err

    def _drain_notifications(self) -> None:
        """Discard stale notification frames before a new request."""
        drained = 0
        while not self._notification_queue.empty():
            self._notification_queue.get_nowait()
            drained += 1
        if drained:
            _LOGGER.debug(
                "Discarded %s stale IQOS notification(s) for %s (%s)",
                drained,
                self._name,
                self._address,
            )

    def _log_last_service_info(self, action: str) -> None:
        """Log Home Assistant's last Bluetooth advertisement for the IQOS."""
        service_info = bluetooth.async_last_service_info(
            self._hass, self._address, connectable=True
        )
        if service_info is None:
            _LOGGER.debug(
                "%s IQOS %s (%s) without cached connectable service info",
                action,
                self._name,
                self._address,
            )
            return

        _LOGGER.debug(
            (
                "%s IQOS %s (%s): source=%s name=%s rssi=%s connectable=%s "
                "service_uuids=%s manufacturer_ids=%s"
            ),
            action,
            self._name,
            self._address,
            service_info.source,
            service_info.name,
            service_info.rssi,
            service_info.connectable,
            service_info.service_uuids,
            list(service_info.manufacturer_data),
        )


class IqosDeviceClient:
    """High-level IQOS operations for one configured device."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        """Initialize the client."""
        self._hass = hass
        self.address = address
        self.name = name
        self._status_commands = {
            AUTOSTART_STATUS_SUBTYPE: LOAD_AUTOSTART_COMMAND,
            SMARTGESTURE_STATUS_SUBTYPE: LOAD_SMARTGESTURE_COMMAND,
        }

    async def async_read_data(self) -> IqosData:
        """Read a full state snapshot from the device."""
        _LOGGER.debug("Starting IQOS data update for %s (%s)", self.name, self.address)
        service_info = bluetooth.async_last_service_info(
            self._hass, self.address, connectable=True
        )
        name = (
            getattr(service_info, "name", None)
            or getattr(getattr(service_info, "device", None), "name", None)
            or self.name
        )
        rssi = getattr(service_info, "rssi", None)
        if service_info is None:
            _LOGGER.debug(
                "No cached connectable Bluetooth service info for IQOS %s (%s)",
                self.name,
                self.address,
            )
        else:
            _LOGGER.debug(
                (
                    "Using cached IQOS service info for %s (%s): source=%s "
                    "name=%s rssi=%s service_uuids=%s"
                ),
                self.name,
                self.address,
                service_info.source,
                service_info.name,
                service_info.rssi,
                service_info.service_uuids,
            )
            if rssi is not None and rssi <= WEAK_RSSI_THRESHOLD:
                _LOGGER.warning(
                    (
                        "IQOS %s (%s) RSSI is very weak (%s dBm); "
                        "BLE GATT connection may fail"
                    ),
                    self.name,
                    self.address,
                    rssi,
                )

        async with IqosBleSession(self._hass, self.address, name) as session:
            device_info = await self._optional(session.read_device_info, DeviceInfo())
            model = model_from_local_name(
                name or device_info.model_number or device_info.serial_number
            )
            data = IqosData(
                address=self.address,
                name=name,
                model=model,
                rssi=rssi,
                device_info=device_info,
            )

            data.battery_level = await self._optional(session.read_battery_level)
            await self._read_status(session, data)
            await self._read_diagnosis(session, data)
            await self._read_settings(session, data)
            _LOGGER.debug(
                (
                    "Finished IQOS data update for %s (%s): model=%s "
                    "battery=%s rssi=%s"
                ),
                data.name,
                data.address,
                data.model,
                data.battery_level,
                data.rssi,
            )
            return data

    async def _read_status(self, session: IqosBleSession, data: IqosData) -> None:
        """Read product numbers, firmware and battery voltage."""
        data.product_number = await self._optional(
            lambda: self._read_product_number(session, ProductNumberKind.STICK)
        )
        data.stick_firmware = await self._optional(
            lambda: self._read_firmware(session, FirmwareKind.STICK)
        )
        if data.model.supports_holder_features:
            data.holder_product_number = await self._optional(
                lambda: self._read_product_number(session, ProductNumberKind.HOLDER)
            )
            data.holder_firmware = await self._optional(
                lambda: self._read_firmware(session, FirmwareKind.HOLDER)
            )
        data.battery_voltage = await self._optional(self._read_battery_voltage(session))

    async def _read_diagnosis(self, session: IqosBleSession, data: IqosData) -> None:
        """Read diagnostic counters."""
        diagnosis = DiagnosticData()
        for command in ALL_DIAGNOSIS_COMMANDS:
            frame = await self._optional(session.request(command))
            if frame is None:
                continue
            diagnosis = parse_diagnosis_response(frame, diagnosis)

        data.total_smoking_count = diagnosis.total_smoking_count
        data.days_used = diagnosis.days_used
        if diagnosis.battery_voltage is not None:
            data.battery_voltage = diagnosis.battery_voltage

    async def _read_settings(self, session: IqosBleSession, data: IqosData) -> None:
        """Read optional user settings."""
        if data.model.supports_brightness:
            data.brightness = await self._optional(self._read_brightness(session))
        if data.model.supports_flexpuff:
            data.flexpuff = await self._optional(self._read_flexpuff(session))
        if data.model.supports_flexbattery:
            data.flexbattery_mode = await self._optional(
                self._read_flexbattery_mode(session)
            )
            data.pause_mode = await self._optional(self._read_pause_mode(session))
        if data.model.supports_autostart:
            data.autostart = await self._optional(self._read_autostart(session))
        if data.model.supports_smartgesture:
            data.smartgesture = await self._optional(self._read_smartgesture(session))
        if data.model.supports_vibration:
            settings = await self._optional(
                lambda: self._read_vibration_settings(session, data.model)
            )
            if settings is not None:
                data.vibration_heating_start = settings.heating_start
                data.vibration_starting_to_use = settings.starting_to_use
                data.vibration_puff_end = settings.puff_end
                data.vibration_manually_terminated = settings.manually_terminated
                data.vibration_charging_start = settings.charging_start

    async def async_set_brightness(self, level: str) -> None:
        """Set LED brightness."""
        await self._send_commands(brightness_commands(level))

    async def async_set_flexpuff(self, enabled: bool) -> None:
        """Enable or disable FlexPuff."""
        await self._send_commands((flexpuff_command(enabled),))

    async def async_set_flexbattery_mode(self, mode: str) -> None:
        """Set FlexBattery mode."""
        await self._send_commands(
            (flexbattery_mode_command(mode), LOAD_FLEXBATTERY_COMMAND)
        )

    async def async_set_pause_mode(self, enabled: bool) -> None:
        """Enable or disable Pause Mode."""
        await self._send_commands((pausemode_command(enabled), LOAD_PAUSEMODE_COMMAND))

    async def async_set_autostart(self, enabled: bool) -> None:
        """Enable or disable Auto Start."""
        await self._send_commands((autostart_command(enabled),))

    async def async_set_smartgesture(self, enabled: bool) -> None:
        """Enable or disable Smart Gesture."""
        await self._send_commands((smartgesture_command(enabled),))

    async def async_set_vibration_setting(
        self, current: IqosData, key: str, enabled: bool
    ) -> None:
        """Update one vibration setting while preserving the other settings."""
        settings = VibrationSettings(
            heating_start=current.vibration_heating_start or False,
            starting_to_use=current.vibration_starting_to_use or False,
            puff_end=current.vibration_puff_end or False,
            manually_terminated=current.vibration_manually_terminated or False,
            charging_start=(
                current.vibration_charging_start
                if current.model.supports_charge_start_vibration
                else None
            ),
        )
        settings = VibrationSettings(
            heating_start=enabled if key == "heating_start" else settings.heating_start,
            starting_to_use=(
                enabled if key == "starting_to_use" else settings.starting_to_use
            ),
            puff_end=enabled if key == "puff_end" else settings.puff_end,
            manually_terminated=(
                enabled
                if key == "manually_terminated"
                else settings.manually_terminated
            ),
            charging_start=(
                enabled if key == "charging_start" else settings.charging_start
            ),
        )
        await self._send_commands(vibration_commands(settings, current.model))

    async def async_find_my_iqos(self) -> None:
        """Vibrate the device briefly so it can be located."""
        async with IqosBleSession(self._hass, self.address, self.name) as session:
            await session.send(START_VIBRATE_COMMAND)
            try:
                await asyncio.sleep(FIND_MY_IQOS_SECONDS)
            finally:
                await session.send(STOP_VIBRATE_COMMAND)

    async def async_lock(self) -> None:
        """Lock the device."""
        await self._send_commands(LOCK_COMMANDS)

    async def async_unlock(self) -> None:
        """Unlock the device."""
        await self._send_commands(UNLOCK_COMMANDS)

    async def _send_commands(self, commands: tuple[bytes, ...]) -> None:
        """Open a short BLE session and send a command sequence."""
        _LOGGER.debug(
            "Sending %s IQOS command(s) to %s (%s)",
            len(commands),
            self.name,
            self.address,
        )
        async with IqosBleSession(self._hass, self.address, self.name) as session:
            for command in commands:
                await session.send(command)

    async def _read_product_number(
        self, session: IqosBleSession, kind: ProductNumberKind
    ) -> str:
        """Read a product number."""
        frame = await session.request(product_number_command(kind))
        return parse_product_number(frame, kind)

    async def _read_firmware(
        self, session: IqosBleSession, kind: FirmwareKind
    ) -> str:
        """Read firmware version."""
        command = (
            LOAD_STICK_FIRMWARE_VERSION_COMMAND
            if kind is FirmwareKind.STICK
            else LOAD_HOLDER_FIRMWARE_VERSION_COMMAND
        )
        frame = await session.request(command)
        return parse_firmware_version(frame, kind)

    async def _read_battery_voltage(self, session: IqosBleSession) -> float | None:
        """Read battery voltage."""
        frame = await session.request(LOAD_BATTERY_VOLTAGE_COMMAND)
        return parse_diagnosis_response(frame).battery_voltage

    async def _read_brightness(self, session: IqosBleSession) -> str:
        """Read brightness."""
        return parse_brightness_response(await session.request(LOAD_BRIGHTNESS_COMMAND))

    async def _read_flexpuff(self, session: IqosBleSession) -> bool:
        """Read FlexPuff state."""
        return parse_flexpuff_response(await session.request(LOAD_FLEXPUFF_COMMAND))

    async def _read_flexbattery_mode(self, session: IqosBleSession) -> str:
        """Read FlexBattery mode."""
        return parse_flexbattery_mode_response(
            await session.request(LOAD_FLEXBATTERY_COMMAND)
        )

    async def _read_pause_mode(self, session: IqosBleSession) -> bool:
        """Read Pause Mode state."""
        return parse_pausemode_response(await session.request(LOAD_PAUSEMODE_COMMAND))

    async def _read_autostart(self, session: IqosBleSession) -> bool:
        """Read Auto Start state."""
        frame = await self._read_toggle_status(
            session, AUTOSTART_STATUS_SUBTYPE, parse_autostart_response
        )
        return parse_autostart_response(frame)

    async def _read_smartgesture(self, session: IqosBleSession) -> bool:
        """Read Smart Gesture state."""
        frame = await self._read_toggle_status(
            session, SMARTGESTURE_STATUS_SUBTYPE, parse_smartgesture_response
        )
        return parse_smartgesture_response(frame)

    async def _read_toggle_status(
        self,
        session: IqosBleSession,
        subtype: int,
        parser: Callable[[bytes], bool],
    ) -> bytes:
        """Read a toggle state, discovering the checksum if needed."""
        command = self._status_commands[subtype]
        try:
            frame = await session.request(command, STATUS_RESPONSE_TIMEOUT)
            parser(frame)
            return frame
        except Exception:
            pass

        for checksum in STATUS_CHECKSUM_CANDIDATES:
            command = toggle_status_command(subtype, checksum)
            try:
                frame = await session.request(command, STATUS_RESPONSE_TIMEOUT)
                parse_toggle_status_response(frame, subtype)
            except Exception:
                continue
            self._status_commands[subtype] = command
            return frame

        raise IqosConnectionError(f"unable to read IQOS toggle subtype {subtype}")

    async def _read_vibration_settings(
        self, session: IqosBleSession, model: DeviceModel
    ) -> VibrationSettings:
        """Read vibration settings."""
        charging_start = None
        if model.supports_charge_start_vibration:
            charging_start = parse_charge_start_vibration_response(
                await session.request(LOAD_VIBRATE_CHARGE_START_COMMAND)
            )
        main_settings = parse_vibration_settings_response(
            await session.request(LOAD_VIBRATION_SETTINGS_COMMAND), model
        )
        return VibrationSettings(
            heating_start=main_settings.heating_start,
            starting_to_use=main_settings.starting_to_use,
            puff_end=main_settings.puff_end,
            manually_terminated=main_settings.manually_terminated,
            charging_start=charging_start,
        )

    async def _optional(
        self,
        value_or_call: Awaitable[_T] | Callable[[], Awaitable[_T]],
        default: _T | None = None,
    ) -> _T | None:
        """Run an optional read and return default on failure."""
        try:
            if callable(value_or_call):
                return await value_or_call()
            return await value_or_call
        except Exception as err:
            _LOGGER.debug("Optional IQOS read failed for %s: %s", self.name, err)
            return default
