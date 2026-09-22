> **Language: English | [中文](README.md)**

AND Home is a [Home Assistant](https://www.home-assistant.io/) custom integration for controlling IoT devices.

**Integration Repository**:
- GitHub: https://github.com/AmateurNoobDog/and_home
- Gitee: https://gitee.com/AmateurNoobDog/and_home

**Firmware Repository**:
- GitHub: https://github.com/AmateurNoobDog/wb2_ha_firmware
- Gitee: https://gitee.com/AmateurNoobDog/wb2_ha_firmware

---

# Device Communication Protocol Documentation

## Overview

AND Home devices communicate using **TCP Socket + JSON line protocol**. The device acts as a TCP server, and the Home Assistant integration connects as a TCP client to send commands.

**Protocol Version**: v2 (Entity-driven architecture)

**Protocol Features**:
- Transport layer: TCP
- Data format: JSON (one message per line, separated by `\n`)
- Connection mode: Short-lived connections (new connection for each request, device auto-disconnects after a few seconds of idle time)
- Default port: 9100
- Entity definition: Device-reported (`get_device` command returns entity list)

---

## Connection Parameters

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| Port | 9100 | Device TCP listening port |
| Timeout | 3.0 seconds | Normal request timeout |
| Scan timeout | 0.3 seconds | Timeout during device discovery |
| Poll interval | 10 seconds | Home Assistant state update frequency |

---

## Request Format

All requests are single-line JSON objects ending with `\n`.

### Get Device Info and Entity Definitions

```json
{"cmd":"get_device"}\n
```

**Returns**: Device basic info and all entity definitions (`Wb2DeviceInfo`).

### Get Entity States

```json
{"cmd":"get_state"}\n
```

**Returns**: Current state of all entities (`Wb2State`, contains `entities[]`).

### Set Entity State

```json
{"cmd":"set","id":"light_01","r":255,"g":0,"b":128}\n
{"cmd":"set","id":"switch_01","on":1}\n
{"cmd":"set","id":"light_01","brightness":128}\n
```

### Send General Commands

```json
{"cmd":"pair"}\n
{"cmd":"reset"}\n
{"cmd":"calibrate"}\n
{"cmd":"restore"}\n
```

### Request Field Description

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cmd` | string | Yes | Command type: `get_device`, `get_state`, `set`, `pair`, `reset`, `calibrate`, `restore` |
| `id` | string | No | Target entity ID (required for `set` command) |
| `r` | int | No | Red channel value (0-255) |
| `g` | int | No | Green channel value (0-255) |
| `b` | int | No | Blue channel value (0-255) |
| `brightness` | int | No | Brightness value (0-255) |
| `on` | int | No | Switch state (0=off, 1=on) |

---

## Response Format

### get_device Response

```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "name": "客厅灯",
  "model": "AND",
  "sw_version": "1.0.0",
  "entities": [
    {"id": "light_01", "type": "light", "name": "主灯", "icon": "mdi:white-balance-sunny"},
    {"id": "switch_01", "type": "switch", "name": "开关1", "icon": "mdi:power"},
    {"id": "switch_02", "type": "switch", "name": "开关2", "icon": "mdi:power"},
    {"id": "radar_01", "type": "binary_sensor", "name": "存在检测", "icon": "mdi:motion-sensor"},
    {"id": "event_01", "type": "event", "name": "遥控器", "icon": "mdi:remote"},
    {"id": "key_01", "type": "sensor", "name": "键值", "icon": "mdi:remote"}
  ]
}
```

### get_state Response

```json
{
  "state": "online",
  "entities": [
    {"id": "light_01", "type": "light", "r": 255, "g": 128, "b": 64, "brightness": 200},
    {"id": "switch_01", "type": "switch", "on": 1},
    {"id": "switch_02", "type": "switch", "on": 0},
    {"id": "radar_01", "type": "binary_sensor", "motion": 1, "presence": 1},
    {"id": "key_01", "type": "sensor", "value": "ABCD1234"}
  ]
}
```

### Response Field Description

#### Wb2DeviceInfo (Device Info)

| Field | Type | Description |
|-------|------|-------------|
| `mac` | string | Device MAC address |
| `name` | string | Device display name |
| `model` | string | Device model |
| `sw_version` | string | Firmware version |
| `entities` | list | Entity definition list |

#### Wb2EntityDef (Entity Definition)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Entity unique identifier |
| `type` | string | Entity type (see type table below) |
| `name` | string | Entity display name |
| `icon` | string | Icon (MDI icon name) |

#### Wb2State (State Response)

| Field | Type | Description |
|-------|------|-------------|
| `state` | string | Device state (`online`/`offline`) |
| `entities` | list | Entity state list |

#### Wb2EntityState (Entity State)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Entity ID |
| `type` | string | Entity type |
| `data` | dict | Entity data (type-dependent) |

---

## Entity Types

| Type | Description | Data Fields |
|------|-------------|-------------|
| `light` | RGB LED light | `r`, `g`, `b`, `brightness` |
| `switch` | Relay switch | `on` (0/1) |
| `binary_sensor` | Binary sensor | `motion`, `presence` (0/1) |
| `sensor` | Data sensor | `value` (string) |
| `event` | Event entity | `event_type`, `event_id` |

### light (RGB Light)

Supported features:
- Color control (RGB)
- Brightness adjustment
- On/off control

Data fields: `r`, `g`, `b`, `brightness`

### switch (Relay Switch)

Supported features:
- On/off control

Data fields: `on` (0=off, 1=on)

### binary_sensor (Binary Sensor)

Supported features:
- Presence detection
- Motion detection

Data fields: `motion`, `presence` (0=none, 1=detected)

### sensor (Data Sensor)

Supported features:
- Key value reporting
- Other numeric data

Data fields: `value` (string)

### event (Event Entity)

Supported features:
- Button press/release events
- Remote control events

Event types: `press`, `release`

---

## Device Discovery Mechanism

Home Assistant integration supports two device discovery methods:

### Zeroconf / mDNS Auto Discovery

Devices broadcast the `_and._tcp` service type via mDNS, allowing Home Assistant to automatically discover AND devices on the local network:

1. **Service Type**: `_and._tcp.local.`
2. **Device Name Format**: `and-{type}-{mac_suffix}` (e.g., `and-light-AABBCC`)
3. **Discovery Flow**: Device broadcasts → HA auto-detects → User confirms addition
4. **DNS Fallback**: Automatically uses cached IP address when connection fails

### TCP Scan Discovery

If Zeroconf discovery fails, devices can be discovered via TCP scanning:

1. **Scan Range**: Iterates through all local network interfaces, generating addresses 1-254 for each subnet
2. **Scan Port**: 9100
3. **Scan Method**: Concurrent scanning (up to 64 concurrent connections)
4. **Scan Timeout**: 0.3 seconds per device
5. **Verification Method**: Sends `{"cmd":"get_device"}` command and checks if response contains valid device info

If auto-discovery fails, users can manually enter the device IP address.

---

## Constant Definitions

```python
# Connection parameters
DEFAULT_PORT = 9100
SCAN_TIMEOUT = 0.3  # Device scan timeout (seconds)
POLL_INTERVAL = 10  # State polling interval (seconds)

# Device types
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_RADAR = "radar"
DEVICE_TYPE_EVENT = "event"
DEVICE_TYPE_KEY_SENSOR = "key_sensor"

# Default values
DEFAULT_NAME = "Light"
DEFAULT_TYPE = "light"
DEFAULT_MODEL = "AND"
DEFAULT_SWITCH_COUNT = 3

# mDNS service type
MDNS_SERVICE_TYPE = "_and._tcp"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_TYPE = "type"
```

---

## Data Structure Definitions (Python)

### Wb2DeviceInfo

```python
from dataclasses import dataclass, field

@dataclass
class Wb2EntityDef:
    """Entity definition"""
    id: str
    type: str
    name: str = ""
    icon: str = ""
    action: str = ""

@dataclass
class Wb2DeviceInfo:
    """Device info"""
    mac: str = ""
    name: str = ""
    model: str = ""
    sw_version: str = ""
    entities: list[Wb2EntityDef] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Wb2DeviceInfo":
        raw_entities = data.get("entities", [])
        entities = []
        for e in raw_entities:
            if isinstance(e, dict) and "id" in e and "type" in e:
                entities.append(Wb2EntityDef(
                    id=e["id"],
                    type=e["type"],
                    name=e.get("name", ""),
                    icon=e.get("icon", ""),
                    action=e.get("action", ""),
                ))
        return cls(
            mac=data.get("mac", ""),
            name=data.get("name", ""),
            model=data.get("model", ""),
            sw_version=data.get("sw_version", ""),
            entities=entities,
        )
```

### Wb2EntityState

```python
@dataclass
class Wb2EntityState:
    """Single entity state"""
    id: str
    type: str
    data: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Wb2EntityState":
        return cls(
            id=d.get("id", ""),
            type=d.get("type", ""),
            data={k: v for k, v in d.items() if k not in ("id", "type")},
        )
```

### Wb2State

```python
@dataclass
class Wb2State:
    """State response"""
    state: str = "online"
    entities: list[Wb2EntityState] = field(default_factory=list)

    def find_entity(self, entity_id: str) -> Wb2EntityState | None:
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "Wb2State":
        raw = data.get("entities", [])
        entities = []
        if isinstance(raw, list):
            for e in raw:
                if isinstance(e, dict):
                    entities.append(Wb2EntityState.from_dict(e))
        return cls(
            state=data.get("state", "online"),
            entities=entities,
        )
```

---

## Code Examples

### Python Async Client

```python
import asyncio
import json

async def get_device_info(host: str, port: int = 9100):
    """Get device info and entity definitions"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b'{"cmd":"get_device"}\n')
        await writer.drain()
        
        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        if line:
            return json.loads(line.decode())
    finally:
        writer.close()
        await writer.wait_closed()

async def get_entity_states(host: str, port: int = 9100):
    """Get all entity states"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        writer.write(b'{"cmd":"get_state"}\n')
        await writer.drain()
        
        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        if line:
            return json.loads(line.decode())
    finally:
        writer.close()
        await writer.wait_closed()

async def set_entity_state(host: str, entity_id: str, params: dict, port: int = 9100):
    """Set entity state"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        cmd = {"cmd": "set", "id": entity_id}
        cmd.update(params)
        writer.write((json.dumps(cmd) + "\n").encode())
        await writer.drain()
        
        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        if line:
            return json.loads(line.decode())
    finally:
        writer.close()
        await writer.wait_closed()

async def send_command(host: str, cmd: str, port: int = 9100):
    """Send general command"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        payload = json.dumps({"cmd": cmd})
        writer.write((payload + "\n").encode())
        await writer.drain()
        
        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        if line:
            return json.loads(line.decode())
    finally:
        writer.close()
        await writer.wait_closed()

# Usage example
async def main():
    host = "192.168.1.100"
    
    # Get device info
    device_info = await get_device_info(host)
    print(f"Device: {device_info['model']} {device_info['name']}")
    print(f"Entity count: {len(device_info['entities'])}")
    
    # Get states
    states = await get_entity_states(host)
    for entity in states["entities"]:
        print(f"  {entity['id']}: {entity.get('data', {})}")
    
    # Set light color
    result = await set_entity_state(host, "light_01", {"r": 255, "g": 0, "b": 128})
    print(f"Set result: {result}")
    
    # Turn on switch
    result = await set_entity_state(host, "switch_01", {"on": 1})
    print(f"Switch result: {result}")
    
    # Calibrate radar
    result = await send_command(host, "calibrate")
    print(f"Calibrate result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### curl Test Commands

```bash
# Get device info
echo '{"cmd":"get_device"}' | nc 192.168.1.100 9100

# Get entity states
echo '{"cmd":"get_state"}' | nc 192.168.1.100 9100

# Set light color
echo '{"cmd":"set","id":"light_01","r":255,"g":0,"b":128}' | nc 192.168.1.100 9100

# Set brightness
echo '{"cmd":"set","id":"light_01","brightness":128}' | nc 192.168.1.100 9100

# Turn on switch
echo '{"cmd":"set","id":"switch_01","on":1}' | nc 192.168.1.100 9100

# 433 pairing
echo '{"cmd":"pair"}' | nc 192.168.1.100 9100

# Calibrate radar
echo '{"cmd":"calibrate"}' | nc 192.168.1.100 9100
```

---

## Firmware Update

### Update Methods

1. **Serial Update**: Using serial tools via UART
2. **OTA Update**: Wireless update over the network (requires firmware support)

### Update Steps

1. Get the latest firmware from Ai-Thinker official
2. Follow device documentation for firmware update
3. Device automatically restarts after update
4. Re-add device in Home Assistant

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Device cannot connect | Check IP address, network connection, firewall settings |
| State not syncing | Restart Home Assistant, check network stability |
| Cannot scan device | Ensure on same LAN, try manual addition |
| Push update failed | Check if port 9101 is occupied |

## Related Links

- [Integration Repo (GitHub)](https://github.com/AmateurNoobDog/and_home)
- [Integration Repo (Gitee)](https://gitee.com/AmateurNoobDog/and_home)
- [Firmware Repo (GitHub)](https://github.com/AmateurNoobDog/wb2_ha_firmware)
- [Firmware Repo (Gitee)](https://gitee.com/AmateurNoobDog/wb2_ha_firmware)
- [Ai-Thinker Official](https://docs.ai-thinker.com/)
- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)

## License

MIT License
