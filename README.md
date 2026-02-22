# LANCOM Management Cloud – Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Integrates the [LANCOM Management Cloud (LMC)](https://cloud.lancom.de) into Home Assistant.

## Features

- **Device status** – online/offline binary sensor per device
- **Account statistics** – total, online and offline device count
- **Device info** – firmware version, model, site, serial number, IP address
- **WAN status** – WAN connection state and traffic counters
- **VPN tunnels** – number of active VPN connections per device
- **Service** – reboot a device from Home Assistant

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
   - **Account ID** – found in the LMC portal URL or account settings

## Entities

### Per Device
| Entity | Type | Description |
|--------|------|-------------|
| Online | Binary Sensor | Device connectivity (online/offline) |
| Firmware Version | Sensor | Installed firmware version |
| Model | Sensor | Device model/type |
| Site | Sensor | Assigned site name |
| Serial Number | Sensor | Device serial number |
| IP Address | Sensor | Current IP address |
| WAN Status | Sensor | WAN connection state + traffic |

### Account
| Entity | Type | Description |
|--------|------|-------------|
| Total Devices | Sensor | Total number of managed devices |
| Online Devices | Sensor | Number of online devices |
| Offline Devices | Sensor | Number of offline devices |

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
