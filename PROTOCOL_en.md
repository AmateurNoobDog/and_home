> **Language: English | [中文](PROTOCOL.md)**

# AND Home Device Communication Protocol

## Overview

AND Home WB2 series devices communicate using **TCP Socket + JSON line protocol**.

- **Protocol Version**: v2 (Entity-driven architecture)
- **Transport Layer**: TCP
- **Data Format**: JSON (one message per line, separated by `\n`)
- **Connection Mode**: Short-lived connections (new connection for each request, device auto-disconnects after a few seconds of idle time)
- **Device Role**: TCP server
- **Integration Role**: TCP client

| Port | Purpose |
|------|---------|
| 9100 | Device TCP listening port (integration connects actively) |
| 9101 | Push port (device connects to integration actively) |

---

## Device Discovery

Home Assistant integration supports three methods to discover devices: Zeroconf auto-discovery, TCP LAN scanning, and manual input.

### Zeroconf / mDNS Auto Discovery

Devices broadcast services via mDNS after startup, and Home Assistant automatically discovers devices on the local network.

**Service Type**: `_and._tcp.local.`

**Device Name Format**: `and-{type}-{mac_suffix}`

- `type`: Device type (e.g., `light`, `switch`)
- `mac_suffix`: Last 6 characters of MAC address (uppercase)

**Example**:

Assuming device MAC is `AA:BB:CC:11:22:33` and device type is `light`:

```
mDNS service name: and-light-AABBCC
mDNS service type: _and._tcp.local.
Port: 9100
```

**Discovery Flow**:

```
Device                          Home Assistant
  |                                |
  |--- mDNS broadcast ------------>|  (Service type: _and._tcp.local.)
  |                                |  Parse name: and-light-AABBCC
  |                                |  Get IP address
  |<---- TCP probe (get_device) ---|  Verify device online
  |---- Response (device info) --->|
  |                                |  Show confirmation dialog
  |<---- User confirms addition ---|
  |                                |  Create config entry
```

### TCP LAN Scanning

When Zeroconf discovery fails, the integration can discover devices via TCP scanning.

**Scan Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Scan port | 9100 | Device TCP listening port |
| Concurrency | 64 | Number of hosts probed simultaneously |
| Per-device timeout | 0.3 seconds | Probe timeout for each host |
| Scan range | All local subnets | Iterates through addresses 1-254 on each interface |

**Verification Method**: Sends `get_device` command to the target port and checks if the response contains a valid `mac` field.

**Scan Request Example**:

```json
{"cmd":"get_device"}\n
```

**Valid Response Example** (device exists):

```json
{"mac":"AA:BB:CC:11:22:33","name":"客厅灯","model":"WB2-Light","entities":[]}
```

**No Response or Invalid Response** (device does not exist):

- Connection timeout
- Empty response
- Response JSON missing `mac` field

### Manual Input

Users can manually enter the device IP address and port number. The integration sends a `get_device` command to verify if the device is online.

**Probe Request**:

```bash
echo '{"cmd":"get_device"}' | nc 192.168.1.100 9100
```

**Valid Response**:

```json
{"mac":"AA:BB:CC:11:22:33","name":"客厅灯","model":"WB2-Light","sw_version":"1.0.0","entities":[{"id":"light_01","type":"light","name":"主灯","icon":"mdi:white-balance-sunny"}]}
```

**Connection Failed**: No response or timeout, integration shows "Cannot connect to device".

---

## Device Info Reporting (get_device)

When the device receives the `get_device` command, it returns basic device info and all entity definitions. The integration uses this command during initialization and scan probing.

### Request Format

```json
{"cmd":"get_device"}\n
```

### Response Format

```json
{
  "mac": "AA:BB:CC:11:22:33",
  "name": "客厅灯",
  "model": "WB2-Light",
  "manufacturer": "Ai-Thinker",
  "sw_version": "1.0.0",
  "entities": [
    {"id": "light_01", "type": "light", "name": "主灯", "icon": "mdi:white-balance-sunny"},
    {"id": "switch_01", "type": "switch", "name": "开关1", "icon": "mdi:power"},
    {"id": "switch_02", "type": "switch", "name": "开关2", "icon": "mdi:power"},
    {"id": "radar_01", "type": "binary_sensor", "name": "存在检测", "icon": "mdi:motion-sensor"},
    {"id": "event_01", "type": "event", "name": "遥控器", "icon": "mdi:remote"},
    {"id": "key_01", "type": "sensor", "name": "键值", "icon": "mdi:remote"},
    {"id": "btn_pair", "type": "button", "name": "433配对", "icon": "mdi:remote", "action": "pair"},
    {"id": "tts_01", "type": "notify", "name": "TTS播报", "icon": "mdi:volume-high"},
    {"id": "vol_01", "type": "number", "name": "音量", "icon": "mdi:volume-high"}
  ]
}
```

### Field Description

#### Device Info Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mac` | string | Yes | Device MAC address (format `AA:BB:CC:DD:EE:FF`) |
| `name` | string | Yes | Device display name |
| `model` | string | Yes | Device model |
| `manufacturer` | string | No | Manufacturer name, not displayed if not returned |
| `sw_version` | string | No | Firmware version |
| `entities` | list | Yes | Entity definition list |

#### Entity Definition Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Entity unique identifier |
| `type` | string | Yes | Entity type (see type table below) |
| `name` | string | No | Entity display name |
| `icon` | string | No | MDI icon name |
| `action` | string | No | Button action command (only for `button` type) |

---

## State Reporting (get_state)

When the device receives the `get_state` command, it returns the current state of all entities. The integration polls every 10 seconds.

### Request Format

```json
{"cmd":"get_state"}\n
```

### Response Format

```json
{
  "state": "online",
  "entities": [
    {"id": "light_01", "type": "light", "r": 255, "g": 128, "b": 64, "brightness": 200},
    {"id": "switch_01", "type": "switch", "on": 1},
    {"id": "switch_02", "type": "switch", "on": 0},
    {"id": "radar_01", "type": "binary_sensor", "motion": 1, "presence": 1},
    {"id": "key_01", "type": "sensor", "value": "ABCD1234"},
    {"id": "event_01", "type": "event", "event_type": "press", "event_id": "btn_1"},
    {"id": "vol_01", "type": "number", "value": 5}
  ]
}
```

### Field Description

#### Top-level Fields

| Field | Type | Description |
|-------|------|-------------|
| `state` | string | Device state: `online` or `offline` |
| `entities` | list | Entity state list |

#### Entity State Fields

Each entity state object contains `id` and `type` fields, with remaining fields varying by entity type.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Entity ID (corresponds to definition in `get_device`) |
| `type` | string | Entity type |
| Other fields | - | Type-specific data fields (see individual type descriptions below) |

---

## State Control (set)

The integration sends `set` commands to the device to control entity states.

### Request Format

```json
{"cmd":"set","id":"<entity_id>",...parameters...}\n
```

### Parameters by Entity Type

#### light (RGB Light)

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `r` | int | 0-255 | Red channel value |
| `g` | int | 0-255 | Green channel value |
| `b` | int | 0-255 | Blue channel value |
| `brightness` | int | 0-255 | Brightness value |

**Set Light Color Example**:

```json
{"cmd":"set","id":"light_01","r":255,"g":0,"b":128}\n
```

**Set Brightness Example**:

```json
{"cmd":"set","id":"light_01","brightness":128}\n
```

**Turn Off Light Example** (all RGB values to 0):

```json
{"cmd":"set","id":"light_01","r":0,"g":0,"b":0}\n
```

#### switch (Relay Switch)

| Parameter | Type | Value | Description |
|-----------|------|-------|-------------|
| `on` | int | 0 or 1 | 0=off, 1=on |

**Turn On Switch Example**:

```json
{"cmd":"set","id":"switch_01","on":1}\n
```

**Turn Off Switch Example**:

```json
{"cmd":"set","id":"switch_01","on":0}\n
```

#### number (Numeric Control)

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `value` | int | 0-9 | Numeric value (e.g., volume level) |

**Set Volume Example**:

```json
{"cmd":"set","id":"vol_01","value":7}\n
```

#### notify (TTS Broadcast)

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | string | Text content to broadcast |

**TTS Broadcast Example**:

```json
{"cmd":"set","id":"tts_01","cmd":"text","text":"欢迎回家"}\n
```

### set Response

After processing the `set` command, the device returns the latest complete state (same format as `get_state` response).

```json
{
  "state": "online",
  "entities": [
    {"id": "light_01", "type": "light", "r": 255, "g": 0, "b": 128, "brightness": 200},
    {"id": "switch_01", "type": "switch", "on": 1}
  ]
}
```

The integration immediately updates HA entity states upon receiving the response, without waiting for the next poll.

---

## General Commands

In addition to `get_device`, `get_state`, and `set`, devices support the following general commands.

### pair (433MHz Pairing)

Enters 433MHz pairing mode, waiting to receive remote control signals.

```json
{"cmd":"pair"}\n
```

### reset (Restart)

Device soft restart.

```json
{"cmd":"reset"}\n
```

### calibrate (Calibration)

Radar sensor calibration (e.g., presence detection sensor).

```json
{"cmd":"calibrate"}\n
```

### restore (Factory Reset)

Restore factory settings.

```json
{"cmd":"restore"}\n
```

### Commands with Entity ID

Some commands can specify a target entity ID:

```json
{"cmd":"pair","id":"event_01"}\n
```

### General Command Response

All general commands return the latest complete state (same format as `get_state` response).

---

## Push Reporting (TCP 9101)

In addition to integration polling, devices can actively push state changes to the integration.

### Working Mechanism

1. Integration starts a TCP push server on `0.0.0.0:9101` during startup
2. When device state changes, it actively connects to the integration's port 9101
3. Push server matches the device by TCP source IP
4. Parses push data and updates HA entity states

### Push Data Format

The data format pushed by devices is identical to the `get_state` response:

```json
{
  "state": "online",
  "entities": [
    {"id": "radar_01", "type": "binary_sensor", "motion": 1, "presence": 1},
    {"id": "event_01", "type": "event", "event_type": "press", "event_id": "btn_1"}
  ]
}
```

### Single Entity Push Format

Some devices may push a single entity's state (e.g., 433 gateway, button sensor):

```json
{"id": "event_01", "type": "event", "event_type": "press", "event_id": "btn_1"}
```

The integration automatically recognizes this format and converts it to the standard `Wb2State` structure.

### Push Flow

```
Device                              Home Assistant
  |                                    |
  |--- TCP connection to 9101 -------->|
  |---- Push data (JSON + \n) -------->|
  |                                    |  Match device by source IP
  |                                    |  Parse Wb2State
  |                                    |  Update HA entity states
  |<---- Connection closed ------------|
```

### IP Matching

The push server matches devices by the TCP connection's source IP address. The integration records the device's IP address during registration (including Zeroconf-discovered IP and configured host).

**Note**: If the device's IP address changes (e.g., DHCP assigns a new IP), push updates will not match the corresponding device. In this case, the polling mechanism still works normally.

---

## Request/Response Field Quick Reference

### Request Commands Overview

| Command | Description | Required Fields | Optional Fields |
|---------|-------------|-----------------|-----------------|
| `get_device` | Get device info and entity definitions | `cmd` | - |
| `get_state` | Get all entity states | `cmd` | - |
| `set` | Set entity state | `cmd`, `id` | `r`, `g`, `b`, `brightness`, `on`, `value`, `text` |
| `pair` | 433MHz pairing | `cmd` | `id` |
| `reset` | Device restart | `cmd` | - |
| `calibrate` | Radar calibration | `cmd` | - |
| `restore` | Factory reset | `cmd` | - |

### Response Fields Overview

#### get_device Response

| Field | Type | Description |
|-------|------|-------------|
| `mac` | string | Device MAC address |
| `name` | string | Device display name |
| `model` | string | Device model |
| `manufacturer` | string | Manufacturer (optional) |
| `sw_version` | string | Firmware version (optional) |
| `entities` | list | Entity definition list |

#### Entity Definition Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Entity unique identifier |
| `type` | string | Entity type |
| `name` | string | Entity display name (optional) |
| `icon` | string | MDI icon name (optional) |
| `action` | string | Button action command (button type only, optional) |

#### get_state / set / Push Response

| Field | Type | Description |
|-------|------|-------------|
| `state` | string | Device state: `online` / `offline` |
| `entities` | list | Entity state list |

#### Entity State Fields (by Type)

**light**:

| Field | Type | Description |
|-------|------|-------------|
| `r` | int | Red channel (0-255) |
| `g` | int | Green channel (0-255) |
| `b` | int | Blue channel (0-255) |
| `brightness` | int | Brightness (0-255) |

**switch**:

| Field | Type | Description |
|-------|------|-------------|
| `on` | int | Switch state (0=off, 1=on) |

**binary_sensor**:

| Field | Type | Description |
|-------|------|-------------|
| `motion` | int | Motion detection (0=none, 1=detected) |
| `presence` | int | Presence detection (0=none, 1=detected) |

**sensor**:

| Field | Type | Description |
|-------|------|-------------|
| `value` | string | Sensor data value |

**event**:

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | Event type: `press` / `release` |
| `event_id` | string | Event identifier |

**number**:

| Field | Type | Description |
|-------|------|-------------|
| `value` | int | Numeric value (0-9) |

---

## Entity Type Overview

| Type | Description | Control Method | Data Fields |
|------|-------------|----------------|-------------|
| `light` | RGB LED light | set (r/g/b/brightness) | r, g, b, brightness |
| `switch` | Relay switch | set (on) | on |
| `binary_sensor` | Binary sensor | Report only | motion, presence |
| `sensor` | Data sensor | Report only | value |
| `event` | Event entity | Report only | event_type, event_id |
| `button` | Button | send_cmd (action) | - |
| `notify` | TTS broadcast | set (text) | - |
| `number` | Numeric control | set (value) | value |

---

## Connection Parameters

| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| `DEFAULT_PORT` | 9100 | Device TCP listening port |
| `PUSH_PORT` | 9101 | Push server port |
| Timeout | 3.0 seconds | Normal request timeout |
| Scan timeout | 0.3 seconds | Device discovery timeout |
| Poll interval | 10 seconds | HA state update frequency |
| Concurrent scan | 64 | TCP scan max concurrent connections |
| Push server retry | 3 times | Retry count when port is occupied |
| Push read timeout | 5.0 seconds | Push data read timeout |

---

## Complete Communication Examples

### Example 1: Device Discovery and Initialization

```
1. Device starts, mDNS broadcasts _and._tcp.local. service
2. HA discovers device, sends get_device to verify

   >>> {"cmd":"get_device"}
   <<< {"mac":"AA:BB:CC:11:22:33","name":"客厅灯","model":"WB2-Light","manufacturer":"Ai-Thinker","sw_version":"1.0.0","entities":[{"id":"light_01","type":"light","name":"主灯","icon":"mdi:white-balance-sunny"},{"id":"switch_01","type":"switch","name":"开关1","icon":"mdi:power"}]}

3. User confirms addition, HA creates config entry
4. HA first poll to get states

   >>> {"cmd":"get_state"}
   <<< {"state":"online","entities":[{"id":"light_01","type":"light","r":255,"g":128,"b":64,"brightness":200},{"id":"switch_01","type":"switch","on":1}]}

5. HA registers push server, device can actively push state changes
```

### Example 2: Light Control

```
1. User turns on light and sets color in HA

   >>> {"cmd":"set","id":"light_01","r":255,"g":0,"b":128,"brightness":200}
   <<< {"state":"online","entities":[{"id":"light_01","type":"light","r":255,"g":0,"b":128,"brightness":200},{"id":"switch_01","type":"switch","on":1}]}

2. Device executes command, returns latest state
3. HA immediately updates entity states (no need to wait for poll)
```

### Example 3: Push Reporting

```
1. Remote control button pressed
2. Device actively connects to HA port 9101

   >>> {"id":"event_01","type":"event","event_type":"press","event_id":"btn_1"}

3. HA matches device by source IP, updates entity state
4. HA triggers corresponding automation
```

### Example 4: Radar Calibration

```
1. User clicks calibration button in HA

   >>> {"cmd":"calibrate","id":"radar_01"}
   <<< {"state":"online","entities":[{"id":"radar_01","type":"binary_sensor","motion":0,"presence":0}]}

2. Device enters calibration mode, returns current state
3. After calibration, device reports new state via push
```
