"""Tests for IQOS protocol helpers."""

from __future__ import annotations

import unittest
from importlib import util
from pathlib import Path
import sys

_PROTOCOL_PATH = Path(__file__).parents[1] / "custom_components" / "iqos" / "protocol.py"
_SPEC = util.spec_from_file_location("iqos_protocol", _PROTOCOL_PATH)
assert _SPEC and _SPEC.loader
protocol = util.module_from_spec(_SPEC)
sys.modules["iqos_protocol"] = protocol
_SPEC.loader.exec_module(protocol)


class ProtocolTest(unittest.TestCase):
    """Protocol parser tests."""

    def test_model_detection(self) -> None:
        """Model names are detected from local-name strings."""
        self.assertEqual(
            protocol.model_from_local_name("IQOS ILUMA i PRIME"),
            protocol.DeviceModel.ILUMA_I_PRIME,
        )
        self.assertEqual(
            protocol.model_from_local_name("IQOS ILUMA ONE"),
            protocol.DeviceModel.ILUMA_ONE,
        )
        self.assertEqual(
            protocol.model_from_local_name("unknown"),
            protocol.DeviceModel.UNKNOWN,
        )

    def test_brightness(self) -> None:
        """Brightness responses are parsed."""
        self.assertEqual(
            protocol.parse_brightness_response(
                bytes([0x00, 0xC0, 0x86, 0x23, 0x64, 0, 0, 0, 0])
            ),
            "high",
        )
        self.assertEqual(
            protocol.parse_brightness_response(
                bytes([0x00, 0xC0, 0x86, 0x23, 0x1E, 0, 0, 0, 0])
            ),
            "low",
        )

    def test_diagnosis(self) -> None:
        """Diagnosis frames accumulate values."""
        data = protocol.parse_diagnosis_response(
            bytes([0x00, 0x08, 0x80, 0x02, 0x1E, 0x00, 0x00, 0x00])
        )
        data = protocol.parse_diagnosis_response(
            bytes([0x00, 0x08, 0x88, 0x21, 0x00, 0xA8, 0x10, 0x00, 0x00]),
            data,
        )
        self.assertEqual(data.days_used, 30)
        self.assertEqual(data.battery_voltage, 4.264)

    def test_product_number(self) -> None:
        """Product number payloads are decoded."""
        frame = bytes([0x00, 0xC0, 0x88, 0x03]) + b"ABCD123456" + bytes([0xAA])
        self.assertEqual(
            protocol.parse_product_number(frame, protocol.ProductNumberKind.STICK),
            "ABCD123456",
        )

    def test_feature_matrix(self) -> None:
        """Model capability helpers match the upstream capability matrix."""
        self.assertTrue(protocol.DeviceModel.ILUMA_I.supports_flexpuff)
        self.assertTrue(protocol.DeviceModel.ILUMA_I_PRIME.supports_flexbattery)
        self.assertFalse(protocol.DeviceModel.ILUMA_ONE.supports_flexpuff)
        self.assertTrue(protocol.DeviceModel.ILUMA_I_ONE.supports_autostart)
        self.assertFalse(protocol.DeviceModel.ILUMA_ONE.supports_smartgesture)
        self.assertTrue(protocol.DeviceModel.ILUMA_PRIME.supports_smartgesture)
        self.assertTrue(protocol.DeviceModel.ILUMA_ONE.supports_vibration)
        self.assertFalse(protocol.DeviceModel.ILUMA_ONE.supports_charge_start_vibration)

    def test_vibration_settings(self) -> None:
        """Vibration settings are parsed and encoded."""
        settings = protocol.parse_vibration_settings_response(
            bytes([0x00, 0x08, 0x84, 0x23, 0x10, 0x00, 0x01, 0x10, 0x77]),
            protocol.DeviceModel.ILUMA_ONE,
        )
        self.assertEqual(
            settings,
            protocol.VibrationSettings(
                heating_start=True,
                starting_to_use=False,
                puff_end=False,
                manually_terminated=True,
            ),
        )
        commands = protocol.vibration_commands(
            protocol.VibrationSettings(
                heating_start=True,
                starting_to_use=False,
                puff_end=True,
                manually_terminated=False,
            ),
            protocol.DeviceModel.ILUMA_ONE,
        )
        self.assertEqual(
            commands[0],
            bytes([0x00, 0xC9, 0x44, 0x23, 0x10, 0x00, 0x01, 0x01, 0x65]),
        )

    def test_smartgesture_status(self) -> None:
        """Smart Gesture status frames are parsed."""
        self.assertTrue(
            protocol.parse_smartgesture_response(
                bytes([0x00, 0x08, 0x87, 0x24, 0x04, 0x01, 0x00, 0x00, 0x00])
            )
        )


if __name__ == "__main__":
    unittest.main()
