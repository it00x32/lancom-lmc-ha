# LANCOM Management Cloud – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/it00x32/lancom-lmc-ha)](https://github.com/it00x32/lancom-lmc-ha/releases)

Integrates the [LANCOM Management Cloud (LMC)](https://cloud.lancom.de) into Home Assistant, providing comprehensive monitoring of all managed network devices.

## Features

- **Device monitoring** – online/offline status, alerts, CPU load, memory usage, temperature
- **WAN status** – connection state, IP, gateway, traffic counters, mobile/LTE details
- **VPN tunnels** – active VPN connection count per device
- **WLAN clients** – connected wireless client count per device
- **Firmware management** – firmware state, update available detection, one-click firmware update
- **Config management** – config sync state, config rollout trigger
- **Lifecycle tracking** – warranty state, end-of-life / end-of-sale detection
- **License pools** – account-level license pool overview
- **Device actions** – reboot, firmware update, config rollout buttons
- **Account statistics** – total, online and offline device counts, active alerts, firmware/config outdated counts

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to **Integrations → Custom repositories**
3. Add `https://github.com/it00x32/lancom-lmc-ha` as **Integration**
4. Search for **LANCOM Management Cloud** and install it
5. Restart Home Assistant

## Manual Installation

1. Copy `custom_components/lancom_lmc/` into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **LANCOM Management Cloud**
3. Enter your credentials:
   - **API Key** – create one under *My Profile → API Keys* in the LMC portal
   - **Account ID** – select from the list of available accounts

### Options

After setup, configure these options via the integration's **Configure** button:

| Option | Default | Description |
|--------|---------|-------------|
| Update Interval | 60 min | How often data is fetched from the LMC API (1–1440 min) |
| Beta Firmware | Off | Use latest (pre-release) firmware instead of stable recommended |
| API Domain | cloud.lancom.de | LMC API domain (change only for custom deployments) |

## Entities

### Per Device – Sensors

| Entity | Type | Description |
|--------|------|-------------|
| Online | Binary Sensor | Device connectivity (online/offline) |
| Alert | Binary Sensor | Active alert on device |
| Firmware Update Available | Binary Sensor | Firmware is outdated |
| Config Outdated | Binary Sensor | Device config out of sync |
| Warranty Expired | Binary Sensor | Warranty has expired |
| End of Life | Binary Sensor | Device reached EOL/EOS lifecycle |
| Firmware Version | Sensor | Installed firmware version |
| Firmware State | Sensor | Firmware status (UP_TO_DATE / OBSOLETE) |
| Model | Sensor | Device model/type |
| Site | Sensor | Assigned site name |
| Serial Number | Sensor | Device serial number |
| IP Address | Sensor | Current IP address |
| Lifecycle | Sensor | Lifecycle status (current / SHIPPING / EOS / EOL) |
| Warranty | Sensor | Warranty state (OK / EXPIRED) |
| WAN Status | Sensor | WAN connection state with traffic attributes |
| WLAN Clients | Sensor | Number of connected wireless clients |
| CPU Load | Sensor | CPU utilization in % |
| Memory Usage | Sensor | Memory utilization in % |
| Temperature | Sensor | Device temperature in °C |

### Per Device – Buttons

| Entity | Description |
|--------|-------------|
| Reboot | Send reboot command to device |
| Firmware Update | Trigger firmware update (stable or beta) |
| Config Rollout | Trigger config rollout to device |

### Account Level

| Entity | Type | Description |
|--------|------|-------------|
| Total Devices | Sensor | Total number of managed devices |
| Online Devices | Sensor | Number of online devices |
| Offline Devices | Sensor | Number of offline devices |
| Active Alerts | Sensor | Number of active alerts |
| Firmware Outdated | Sensor | Number of devices with outdated firmware |
| Config Outdated | Sensor | Number of devices with outdated config |
| License Pools | Sensor | Number of license pools (details as attributes) |
| Last Sync | Sensor | Timestamp of last successful API sync |
| Update API now | Button | Trigger an immediate data refresh |

## Services

### `lancom_lmc.reboot_device`

Sends a reboot command to a device.

```yaml
service: lancom_lmc.reboot_device
data:
  device_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

## API Reference

- [Devices API](https://cloud.lancom.de/cloud-service-devices/api-docs/)
- [Monitoring API](https://cloud.lancom.de/cloud-service-monitoring/api-docs/)
- [Auth API](https://cloud.lancom.de/cloud-service-auth/api-docs/)
- [Licenses API](https://cloud.lancom.de/cloud-service-licenses/api-docs/)
