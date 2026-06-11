"""IQOS BLE protocol helpers.

This module ports the frame constants and parsers from the GPL-3.0 Rust
`hauntedfail/iqos` crate, which is the protocol source of truth for IQOS
command encoding, response parsing, and capability gating. Home Assistant keeps
the BLE transport, config flow, and entity layer in Python so the custom
integration remains HACS-installable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto

DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
IQOS_CORE_SERVICE_UUID = "daebb240-b041-11e4-9e45-0002a5d5c51b"
BATTERY_CHARACTERISTIC_UUID = "f8a54120-b041-11e4-9be7-0002a5d5c51b"
SCP_CONTROL_CHARACTERISTIC_UUID = "e16c6e20-b041-11e4-a4c3-0002a5d5c51b"

MODEL_NUMBER_CHARACTERISTIC_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
SERIAL_NUMBER_CHARACTERISTIC_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
SOFTWARE_REVISION_CHARACTERISTIC_UUID = "00002a28-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_CHARACTERISTIC_UUID = "00002a29-0000-1000-8000-00805f9b34fb"

LOAD_BRIGHTNESS_COMMAND = bytes([0x00, 0xC0, 0x02, 0x23, 0xC3])
SET_BRIGHTNESS_HIGH_COMMANDS = (
    bytes([0x00, 0xC0, 0x46, 0x23, 0x64, 0x00, 0x00, 0x00, 0x4F]),
    LOAD_BRIGHTNESS_COMMAND,
    bytes([0x00, 0xC9, 0x44, 0x24, 0x64, 0x00, 0x00, 0x00, 0x34]),
)
SET_BRIGHTNESS_LOW_COMMANDS = (
    bytes([0x00, 0xC0, 0x46, 0x23, 0x1E, 0x00, 0x00, 0x00, 0xE1]),
    LOAD_BRIGHTNESS_COMMAND,
    bytes([0x00, 0xC9, 0x44, 0x24, 0x1E, 0x00, 0x00, 0x00, 0x9A]),
)

LOAD_TELEMETRY_COMMAND = bytes([0x00, 0xC9, 0x10, 0x02, 0x01, 0x01, 0x75, 0xD6])
LOAD_TIMESTAMP_COMMAND = bytes([0x00, 0xC0, 0x10, 0x02, 0x00, 0x04, 0x38, 0xEF])
LOAD_BATTERY_VOLTAGE_COMMAND = bytes([0x00, 0xC0, 0x00, 0x21, 0xE7])
ALL_DIAGNOSIS_COMMANDS = (
    LOAD_TELEMETRY_COMMAND,
    LOAD_TIMESTAMP_COMMAND,
    LOAD_TELEMETRY_COMMAND,
    LOAD_BATTERY_VOLTAGE_COMMAND,
)

LOAD_STICK_FIRMWARE_VERSION_COMMAND = bytes(
    [0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00]
)
LOAD_HOLDER_FIRMWARE_VERSION_COMMAND = bytes(
    [0x00, 0xC9, 0x00, 0x00, 0x00, 0x00, 0x00]
)

PRODUCT_NUMBER_COMMAND = bytes([0x00, 0xC0, 0x00, 0x03, 0x09])
HOLDER_PRODUCT_NUMBER_COMMAND = bytes([0x00, 0xC9, 0x00, 0x03, 0x09])

LOAD_FLEXPUFF_COMMAND = bytes([0x00, 0xD2, 0x05, 0x22, 0x03, 0x00, 0x00, 0x00, 0x17])
FLEXPUFF_ENABLE_COMMAND = bytes([0x00, 0xD2, 0x45, 0x22, 0x03, 0x01, 0x00, 0x00, 0x0A])
FLEXPUFF_DISABLE_COMMAND = bytes([0x00, 0xD2, 0x45, 0x22, 0x03, 0x00, 0x00, 0x00, 0x0A])

LOAD_FLEXBATTERY_COMMAND = bytes([0x00, 0xC9, 0x00, 0x25, 0xFB])
LOAD_PAUSEMODE_COMMAND = bytes([0x00, 0xC9, 0x07, 0x24, 0x02, 0x00, 0x00, 0x00, 0x18])
FLEXBATTERY_ECO_SET_COMMAND = bytes([0x00, 0xC9, 0x44, 0x25, 0x01, 0x00, 0x00, 0x00, 0x4D])
FLEXBATTERY_PERFORMANCE_SET_COMMAND = bytes(
    [0x00, 0xC9, 0x44, 0x25, 0x00, 0x00, 0x00, 0x00, 0x5B]
)
PAUSEMODE_ENABLE_SET_COMMAND = bytes([0x00, 0xC9, 0x47, 0x24, 0x02, 0x01, 0x00, 0x00, 0x05])
PAUSEMODE_DISABLE_SET_COMMAND = bytes([0x00, 0xC9, 0x47, 0x24, 0x02, 0x00, 0x00, 0x00, 0x6E])

AUTOSTART_ENABLE_COMMAND = bytes([0x00, 0xC9, 0x47, 0x24, 0x01, 0x01, 0x00, 0x00, 0x3F])
AUTOSTART_DISABLE_COMMAND = bytes([0x00, 0xC9, 0x47, 0x24, 0x01, 0x00, 0x00, 0x00, 0x54])
LOAD_AUTOSTART_COMMAND = bytes([0x00, 0xC9, 0x07, 0x24, 0x01, 0x00, 0x00, 0x00, 0x22])
SMARTGESTURE_ENABLE_COMMAND = bytes([0x00, 0xC9, 0x47, 0x24, 0x04, 0x01, 0x00, 0x00, 0x3C])
SMARTGESTURE_DISABLE_COMMAND = bytes([0x00, 0xC9, 0x47, 0x24, 0x04, 0x00, 0x00, 0x00, 0x57])
LOAD_SMARTGESTURE_COMMAND = bytes([0x00, 0xC9, 0x07, 0x24, 0x04, 0x00, 0x00, 0x00, 0x08])
AUTOSTART_STATUS_SUBTYPE = 0x01
SMARTGESTURE_STATUS_SUBTYPE = 0x04
STATUS_CHECKSUM_CANDIDATES = (
    0x18,
    0x08,
    0x17,
    0x16,
    0x19,
    0x1A,
    0x1F,
    0x20,
    0x21,
    0x22,
    0x2C,
    0x2F,
    0xC2,
    0xCF,
    0xFD,
    0xFE,
)

LOAD_VIBRATION_SETTINGS_COMMAND = bytes([0x00, 0xC9, 0x00, 0x23, 0xE9])
LOAD_VIBRATE_CHARGE_START_COMMAND = bytes(
    [0x00, 0xC9, 0x07, 0x04, 0x04, 0x00, 0x00, 0x00, 0x08]
)
START_VIBRATE_COMMAND = bytes([0x00, 0xC0, 0x45, 0x22, 0x01, 0x1E, 0x00, 0x00, 0xC3])
STOP_VIBRATE_COMMAND = bytes([0x00, 0xC0, 0x45, 0x22, 0x00, 0x1E, 0x00, 0x00, 0xD5])

WHEN_CHARGE_START_ON_RESPONSE = bytes(
    [
        0x00,
        0x08,
        0x8B,
        0x04,
        0x04,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x56,
    ]
)
WHEN_CHARGE_START_OFF_RESPONSE = bytes(
    [
        0x00,
        0x08,
        0x8B,
        0x04,
        0x04,
        0x00,
        0x00,
        0x00,
        0x00,
        0x09,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0x00,
        0xEE,
    ]
)
WHEN_CHARGING_START_ON_COMMANDS = (
    bytes(
        [
            0x01,
            0xC9,
            0x4F,
            0x04,
            0x5B,
            0x04,
            0x00,
            0xFF,
            0xFF,
            0xFF,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    ),
    bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06]),
    bytes(
        [
            0x01,
            0xC9,
            0x4F,
            0x04,
            0x72,
            0x05,
            0x00,
            0xFF,
            0xFF,
            0xFF,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    ),
    bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x72]),
    bytes([0x00, 0xC9, 0x47, 0x04, 0x00, 0xFF, 0xFF, 0x00, 0xDA]),
    bytes([0x00, 0xC9, 0x07, 0x04, 0x04, 0x00, 0x00, 0x00, 0x08]),
    bytes([0x00, 0xC9, 0x07, 0x04, 0x05, 0x00, 0x00, 0x00, 0x1E]),
)
WHEN_CHARGING_START_OFF_COMMANDS = (
    bytes(
        [
            0x01,
            0xC9,
            0x4F,
            0x04,
            0x64,
            0x04,
            0x00,
            0xFF,
            0xFF,
            0xFF,
            0x09,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    ),
    bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0C]),
    bytes(
        [
            0x01,
            0xC9,
            0x4F,
            0x04,
            0x4D,
            0x05,
            0x00,
            0xFF,
            0xFF,
            0xFF,
            0x09,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]
    ),
    bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x78]),
    bytes([0x00, 0xC9, 0x47, 0x04, 0x00, 0xFF, 0xFF, 0x00, 0xDA]),
    bytes([0x00, 0xC9, 0x07, 0x04, 0x04, 0x00, 0x00, 0x00, 0x08]),
    bytes([0x00, 0xC9, 0x07, 0x04, 0x05, 0x00, 0x00, 0x00, 0x1E]),
)

LOCK_COMMANDS = (
    bytes([0x00, 0xC9, 0x44, 0x04, 0x02, 0xFF, 0x00, 0x00, 0x5A]),
    bytes([0x00, 0xC9, 0x00, 0x04, 0x1C]),
    bytes([0x00, 0xC0, 0x01, 0x00, 0xF6]),
)
UNLOCK_COMMANDS = (
    bytes([0x00, 0xC9, 0x44, 0x04, 0x00, 0x00, 0x00, 0x00, 0x5D]),
    bytes([0x00, 0xC9, 0x00, 0x04, 0x1C]),
    bytes([0x00, 0xC0, 0x01, 0x00, 0xF6]),
)


class IqosProtocolError(ValueError):
    """Raised when an IQOS protocol frame cannot be decoded."""


class DeviceModel(StrEnum):
    """Known IQOS device models."""

    ILUMA_ONE = auto()
    ILUMA = auto()
    ILUMA_PRIME = auto()
    ILUMA_I_ONE = auto()
    ILUMA_I = auto()
    ILUMA_I_PRIME = auto()
    UNKNOWN = auto()

    @property
    def display_name(self) -> str | None:
        """Return a user-facing model name."""
        return {
            DeviceModel.ILUMA_ONE: "IQOS ILUMA ONE",
            DeviceModel.ILUMA: "IQOS ILUMA",
            DeviceModel.ILUMA_PRIME: "IQOS ILUMA PRIME",
            DeviceModel.ILUMA_I_ONE: "IQOS ILUMA i ONE",
            DeviceModel.ILUMA_I: "IQOS ILUMA i",
            DeviceModel.ILUMA_I_PRIME: "IQOS ILUMA i PRIME",
            DeviceModel.UNKNOWN: None,
        }[self]

    @property
    def supports_holder_features(self) -> bool:
        """Return true if the model exposes holder-specific metadata."""
        return self in {
            DeviceModel.ILUMA,
            DeviceModel.ILUMA_PRIME,
            DeviceModel.ILUMA_I,
            DeviceModel.ILUMA_I_PRIME,
        }

    @property
    def supports_brightness(self) -> bool:
        """Return true if brightness control is supported."""
        return self is not DeviceModel.UNKNOWN

    @property
    def supports_device_lock(self) -> bool:
        """Return true if lock and unlock commands are supported."""
        return self is not DeviceModel.UNKNOWN

    @property
    def supports_flexpuff(self) -> bool:
        """Return true if FlexPuff is supported."""
        return self in {DeviceModel.ILUMA_I, DeviceModel.ILUMA_I_PRIME}

    @property
    def supports_flexbattery(self) -> bool:
        """Return true if FlexBattery is supported."""
        return self in {DeviceModel.ILUMA_I, DeviceModel.ILUMA_I_PRIME}

    @property
    def supports_autostart(self) -> bool:
        """Return true if Auto Start is supported."""
        return self in {
            DeviceModel.ILUMA_I_ONE,
            DeviceModel.ILUMA_I,
            DeviceModel.ILUMA_I_PRIME,
        }

    @property
    def supports_smartgesture(self) -> bool:
        """Return true if Smart Gesture is supported."""
        return self in {
            DeviceModel.ILUMA,
            DeviceModel.ILUMA_PRIME,
            DeviceModel.ILUMA_I_ONE,
            DeviceModel.ILUMA_I,
            DeviceModel.ILUMA_I_PRIME,
        }

    @property
    def supports_vibration(self) -> bool:
        """Return true if vibration settings are supported."""
        return self is not DeviceModel.UNKNOWN

    @property
    def supports_charge_start_vibration(self) -> bool:
        """Return true if charge-start vibration is supported."""
        return self in {
            DeviceModel.ILUMA,
            DeviceModel.ILUMA_PRIME,
            DeviceModel.ILUMA_I,
            DeviceModel.ILUMA_I_PRIME,
        }


class FirmwareKind(StrEnum):
    """Firmware target kind."""

    STICK = auto()
    HOLDER = auto()


class ProductNumberKind(StrEnum):
    """Product-number target kind."""

    STICK = auto()
    HOLDER = auto()


@dataclass(slots=True)
class DeviceInfo:
    """Standard BLE Device Information fields."""

    model_number: str | None = None
    serial_number: str | None = None
    software_revision: str | None = None
    manufacturer_name: str | None = None


@dataclass(slots=True)
class DiagnosticData:
    """Diagnostic telemetry read from IQOS SCP commands."""

    total_smoking_count: int | None = None
    days_used: int | None = None
    battery_voltage: float | None = None


@dataclass(frozen=True, slots=True)
class VibrationSettings:
    """Vibration setting snapshot."""

    heating_start: bool
    starting_to_use: bool
    puff_end: bool
    manually_terminated: bool
    charging_start: bool | None = None


def model_from_local_name(value: str | None) -> DeviceModel:
    """Infer an IQOS model from a BLE local-name string."""
    if not value:
        return DeviceModel.UNKNOWN

    normalized = value.strip().upper()
    if "ILUMA I PRIME" in normalized:
        return DeviceModel.ILUMA_I_PRIME
    if "ILUMA I ONE" in normalized:
        return DeviceModel.ILUMA_I_ONE
    if "ILUMA I" in normalized:
        return DeviceModel.ILUMA_I
    if "ILUMA PRIME" in normalized:
        return DeviceModel.ILUMA_PRIME
    if "ILUMA ONE" in normalized:
        return DeviceModel.ILUMA_ONE
    if "ILUMA" in normalized:
        return DeviceModel.ILUMA
    return DeviceModel.UNKNOWN


def is_iqos_name(value: str | None) -> bool:
    """Return true if a BLE local name looks like an IQOS device."""
    return bool(value and "IQOS" in value.upper())


def parse_battery_level(frame: bytes) -> int:
    """Parse the IQOS battery characteristic frame."""
    if len(frame) == 1:
        return frame[0]
    if len(frame) >= 3:
        return frame[2]
    raise IqosProtocolError("battery characteristic frame too short")


def parse_brightness_response(frame: bytes) -> str:
    """Parse a brightness response into `high` or `low`."""
    if len(frame) < 9:
        raise IqosProtocolError("invalid brightness response: frame too short")
    if frame[:4] != bytes([0x00, 0xC0, 0x86, 0x23]):
        raise IqosProtocolError("invalid brightness response: header mismatch")
    if frame[4] == 0x64:
        return "high"
    if frame[4] == 0x1E:
        return "low"
    raise IqosProtocolError("invalid brightness response: unknown level flag")


def brightness_commands(level: str) -> tuple[bytes, ...]:
    """Return the command sequence required to set the brightness level."""
    match level:
        case "high":
            return SET_BRIGHTNESS_HIGH_COMMANDS
        case "low":
            return SET_BRIGHTNESS_LOW_COMMANDS
        case _:
            raise IqosProtocolError(f"invalid brightness level: {level}")


def parse_firmware_version(frame: bytes, kind: FirmwareKind) -> str:
    """Parse a firmware response frame."""
    if len(frame) < 10:
        raise IqosProtocolError("invalid firmware response: frame too short")
    expected_second_byte = 0xC0 if kind is FirmwareKind.STICK else 0x08
    if frame[:4] != bytes([0x00, expected_second_byte, 0x88, 0x00]):
        raise IqosProtocolError("invalid firmware response: header mismatch")
    return f"v{frame[6]}.{frame[7]}.{frame[8]}.{frame[9]}"


def product_number_command(kind: ProductNumberKind) -> bytes:
    """Return the product-number request command for a target kind."""
    if kind is ProductNumberKind.STICK:
        return PRODUCT_NUMBER_COMMAND
    return HOLDER_PRODUCT_NUMBER_COMMAND


def parse_product_number(frame: bytes, kind: ProductNumberKind) -> str:
    """Parse a product-number response into a printable string."""
    prefix = (
        bytes([0x00, 0xC0, 0x88, 0x03])
        if kind is ProductNumberKind.STICK
        else bytes([0x00, 0x08, 0x88, 0x03])
    )
    if len(frame) < len(prefix) or frame[: len(prefix)] != prefix:
        raise IqosProtocolError("invalid product number response: header mismatch")

    if kind is ProductNumberKind.STICK:
        if len(frame) <= len(prefix) + 1:
            raise IqosProtocolError("invalid product number response: missing stick payload")
        payload = frame[len(prefix) : -1]
    else:
        if len(frame) <= len(prefix):
            raise IqosProtocolError("invalid product number response: missing holder payload")
        payload = frame[len(prefix) :]

    return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in payload)


def parse_diagnosis_response(frame: bytes, data: DiagnosticData | None = None) -> DiagnosticData:
    """Parse a diagnostic response and merge it into existing diagnostic data."""
    if data is None:
        data = DiagnosticData()
    if len(frame) < 4:
        raise IqosProtocolError("diagnosis response too short for header")

    header = (frame[2], frame[3])
    if header == (0x90, 0x22):
        _parse_telemetry_response(frame, data)
    elif header == (0x80, 0x02):
        if len(frame) < 6:
            raise IqosProtocolError("invalid timestamp frame: too short")
        data.days_used = int.from_bytes(frame[4:6], "little")
    elif header == (0x88, 0x21):
        if len(frame) < 7:
            raise IqosProtocolError("invalid battery voltage frame: too short")
        data.battery_voltage = int.from_bytes(frame[5:7], "little") / 1000.0
    return data


def _parse_telemetry_response(frame: bytes, data: DiagnosticData) -> None:
    """Parse telemetry blocks from a diagnostic response."""
    if len(frame) < 6:
        raise IqosProtocolError("invalid telemetry frame: too short for marker")
    if int.from_bytes(frame[4:6], "little") != 0x0101:
        raise IqosProtocolError("invalid telemetry frame: wrong marker")

    num_blocks = max(frame[3] - 2, 0) // 8
    blocks_start = 6
    required = blocks_start + num_blocks * 8
    if len(frame) < required:
        raise IqosProtocolError(
            f"invalid telemetry frame: expected {required} bytes, got {len(frame)}"
        )

    for index in range(num_blocks):
        offset = blocks_start + index * 8
        block = frame[offset : offset + 8]
        value = int.from_bytes(block[4:6], "little")
        tag = block[7]
        if tag == 0x8E:
            data.total_smoking_count = value
        elif tag == 0x17:
            data.days_used = value


def parse_flexpuff_response(frame: bytes) -> bool:
    """Parse a FlexPuff response frame."""
    if len(frame) < 9:
        raise IqosProtocolError("invalid FlexPuff response: frame too short")
    if frame[:5] != bytes([0x00, 0x90, 0x85, 0x22, 0x03]):
        raise IqosProtocolError("invalid FlexPuff response: header mismatch")
    if frame[5] == 0x01:
        return True
    if frame[5] == 0x00:
        return False
    raise IqosProtocolError("invalid FlexPuff response: unknown flag byte")


def flexpuff_command(enabled: bool) -> bytes:
    """Return the FlexPuff write command."""
    return FLEXPUFF_ENABLE_COMMAND if enabled else FLEXPUFF_DISABLE_COMMAND


def parse_flexbattery_mode_response(frame: bytes) -> str:
    """Parse a FlexBattery mode response."""
    if len(frame) < 9:
        raise IqosProtocolError("invalid FlexBattery response: frame too short")
    if frame[:4] != bytes([0x00, 0x08, 0x84, 0x25]):
        raise IqosProtocolError("invalid FlexBattery response: header mismatch")
    if frame[4] == 0x00:
        return "performance"
    if frame[4] == 0x01:
        return "eco"
    raise IqosProtocolError("invalid FlexBattery response: unknown mode byte")


def flexbattery_mode_command(mode: str) -> bytes:
    """Return the FlexBattery mode write command."""
    match mode:
        case "performance":
            return FLEXBATTERY_PERFORMANCE_SET_COMMAND
        case "eco":
            return FLEXBATTERY_ECO_SET_COMMAND
        case _:
            raise IqosProtocolError(f"invalid FlexBattery mode: {mode}")


def parse_pausemode_response(frame: bytes) -> bool:
    """Parse a Pause Mode response."""
    if len(frame) < 9:
        raise IqosProtocolError("invalid Pause Mode response: frame too short")
    if frame[:4] != bytes([0x00, 0x08, 0x87, 0x24]):
        raise IqosProtocolError("invalid Pause Mode response: header mismatch")
    if frame[5] == 0x00:
        return False
    if frame[5] == 0x01:
        return True
    raise IqosProtocolError("invalid Pause Mode response: unknown flag byte")


def pausemode_command(enabled: bool) -> bytes:
    """Return the Pause Mode write command."""
    return PAUSEMODE_ENABLE_SET_COMMAND if enabled else PAUSEMODE_DISABLE_SET_COMMAND


def parse_autostart_response(frame: bytes) -> bool:
    """Parse an Auto Start response."""
    return parse_toggle_status_response(frame, AUTOSTART_STATUS_SUBTYPE)


def parse_smartgesture_response(frame: bytes) -> bool:
    """Parse a Smart Gesture response."""
    return parse_toggle_status_response(frame, SMARTGESTURE_STATUS_SUBTYPE)


def parse_toggle_status_response(frame: bytes, subtype: int) -> bool:
    """Parse a generic IQOS toggle-status response."""
    if len(frame) < 9:
        raise IqosProtocolError("invalid toggle status response: frame too short")
    if (
        frame[0] != 0x00
        or frame[1] != 0x08
        or frame[2] != 0x87
        or frame[3] != 0x24
        or frame[4] != subtype
    ):
        raise IqosProtocolError("invalid toggle status response: header mismatch")
    if frame[5] == 0x00:
        return False
    if frame[5] == 0x01:
        return True
    raise IqosProtocolError("invalid toggle status response: unknown flag byte")


def autostart_command(enabled: bool) -> bytes:
    """Return the Auto Start write command."""
    return AUTOSTART_ENABLE_COMMAND if enabled else AUTOSTART_DISABLE_COMMAND


def smartgesture_command(enabled: bool) -> bytes:
    """Return the Smart Gesture write command."""
    return SMARTGESTURE_ENABLE_COMMAND if enabled else SMARTGESTURE_DISABLE_COMMAND


def toggle_status_command(subtype: int, checksum: int) -> bytes:
    """Build an experimental toggle-status read command."""
    return bytes([0x00, 0xC9, 0x07, 0x24, subtype, 0x00, 0x00, 0x00, checksum])


def parse_vibration_settings_response(
    frame: bytes, model: DeviceModel
) -> VibrationSettings:
    """Parse the main vibration settings response frame."""
    if len(frame) < 9:
        raise IqosProtocolError("invalid vibration response: frame too short")
    if frame[:4] != bytes([0x00, 0x08, 0x84, 0x23]):
        raise IqosProtocolError("invalid vibration response: header mismatch")
    if model.supports_charge_start_vibration:
        if frame[4] not in (0x10, 0x03):
            raise IqosProtocolError("invalid vibration response: header mismatch")
    elif frame[4] != 0x10:
        raise IqosProtocolError("invalid vibration response: header mismatch")

    heat_use_byte = frame[6]
    end_terminated_byte = frame[7]
    return VibrationSettings(
        heating_start=bool(heat_use_byte & 0x01),
        starting_to_use=bool(heat_use_byte & 0x10),
        puff_end=bool(end_terminated_byte & 0x01),
        manually_terminated=bool(end_terminated_byte & 0x10),
    )


def parse_charge_start_vibration_response(frame: bytes) -> bool:
    """Parse charge-start vibration state."""
    if len(frame) < 19:
        raise IqosProtocolError("invalid charge-start vibration response: frame too short")
    if frame == WHEN_CHARGE_START_ON_RESPONSE:
        return True
    if frame == WHEN_CHARGE_START_OFF_RESPONSE:
        return False
    return frame[8] == 0x01


def vibration_commands(settings: VibrationSettings, model: DeviceModel) -> tuple[bytes, ...]:
    """Build the vibration setting update command sequence."""
    commands = [_main_vibration_command(settings)]
    if model.supports_charge_start_vibration:
        if settings.charging_start is None:
            raise IqosProtocolError("charge-start vibration value is required")
        if settings.charging_start:
            commands.extend(WHEN_CHARGING_START_ON_COMMANDS)
        elif any(
            (
                settings.heating_start,
                settings.starting_to_use,
                settings.puff_end,
                settings.manually_terminated,
            )
        ):
            commands.extend(WHEN_CHARGING_START_OFF_COMMANDS)
    return tuple(commands)


def _main_vibration_command(settings: VibrationSettings) -> bytes:
    """Build the main vibration register write command."""
    register = 0
    if settings.heating_start:
        register |= 0x0100
    if settings.starting_to_use:
        register |= 0x1000
    if settings.puff_end:
        register |= 0x0001
    if settings.manually_terminated:
        register |= 0x0010
    return bytes(
        [
            0x00,
            0xC9,
            0x44,
            0x23,
            0x10,
            0x00,
            (register >> 8) & 0xFF,
            register & 0xFF,
            _vibration_checksum(register),
        ]
    )


def _vibration_checksum(register: int) -> int:
    """Calculate the vibration settings checksum."""
    checksum = 0x77
    if register & 0x0001:
        checksum ^= 0x07
    if register & 0x0010:
        checksum ^= 0x70
    if register & 0x0100:
        checksum ^= 0x15
    if register & 0x1000:
        checksum ^= 0x57
    return checksum
