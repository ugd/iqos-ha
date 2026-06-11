# IQOS for Home Assistant

Custom Home Assistant integration for IQOS ILUMA devices over Bluetooth Low
Energy. It is designed for HACS and uses Home Assistant's Bluetooth stack, so it
works through ESPHome Bluetooth Proxy devices already configured in Home
Assistant. It does not use USB, cloud APIs, the IQOS app, or an external CLI.

## Features

- Multiple IQOS devices, one Home Assistant config entry per device.
- Bluetooth discovery for devices advertising as `IQOS*` or the IQOS core
  service UUID.
- Battery level, battery voltage, puff count, days used, RSSI, firmware and
  product-number sensors.
- Brightness select.
- FlexPuff, FlexBattery, Pause Mode, Auto Start, Smart Gesture and vibration
  setting entities where the detected model supports them.
- Find My IQOS, Lock and Unlock buttons.

## Device Compatibility

The integration exposes the supported entities per detected model:

| Feature | ILUMA i | ILUMA i One | ILUMA i Prime | ILUMA | ILUMA ONE | ILUMA Prime |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Battery Status | yes | yes | yes | yes | yes | yes |
| Device Info | yes | yes | yes | yes | yes | yes |
| Diagnosis | yes | yes | yes | yes | yes | yes |
| Find My IQOS | yes | yes | yes | yes | yes | yes |
| Device Lock/Unlock | yes | yes | yes | yes | yes | yes |
| Vibration Settings | yes | yes | yes | yes | yes | yes |
| Brightness | yes | yes | yes | yes | yes | yes |
| Auto Start | yes | yes | yes | no | no | no |
| Smart Gesture | yes | yes | yes | yes | no | yes |
| Flex Puff | yes | no | yes | no | no | no |
| Flex Battery | yes | no | yes | no | no | no |

Holder-based models expose the extra charge-start vibration setting.

## Installation with HACS

1. In HACS, add this repository as a custom repository of type `Integration`.
   Use this URL: `https://github.com/ugd/iqos-ha`
2. Install the `IQOS` integration.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration > IQOS**.
5. Keep each IQOS device nearby and awake while adding it.

## Bluetooth Proxy

This integration is intended to work through Home Assistant's Bluetooth manager.
For an ESPHome Bluetooth Proxy, make sure the proxy has active BLE/GATT
connections enabled. Recent ESPHome versions default `bluetooth_proxy.active` to
`true`, but older or custom YAML may need it explicitly:

```yaml
esp32_ble_tracker:

bluetooth_proxy:
  active: true
```

In Home Assistant, the ESPHome device should be online and visible under
**Settings > Devices & services > Bluetooth**. If you add multiple IQOS devices,
keep them close enough to a proxy and avoid polling too aggressively because
ESP32 proxies have a limited number of simultaneous active BLE connections.

## Notes

This integration opens short BLE connections for updates and commands. If a
device is asleep, out of range, or no connectable Bluetooth proxy can reach it,
its entities will become unavailable until Home Assistant can reach it again.

The protocol constants and parsers are based on the GPL-3.0
[`V-VX/iqos`](https://github.com/V-VX/iqos) Rust project and the
[`nsoclub/iqos_cli`](https://github.com/nsoclub/iqos_cli) CLI that uses it.
