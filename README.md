> **Language: [English](README_en.md) | 中文**

AND Home 是一个 [Home Assistant](https://www.home-assistant.io/) 自定义集成，用于控制 IoT 设备。

**集成仓库**:
- GitHub: https://github.com/AmateurNoobDog/and_home
- Gitee: https://gitee.com/AmateurNoobDog/and_home

**固件仓库**:
- GitHub: https://github.com/AmateurNoobDog/wb2_ha_firmware
- Gitee: https://gitee.com/AmateurNoobDog/wb2_ha_firmware

---

# 设备通信协议文档

## 概述

AND Home 设备使用 **TCP Socket + JSON 行协议** 进行通信。设备作为 TCP 服务器，Home Assistant 集成作为客户端连接设备并发送命令。

**协议版本**: v2（实体驱动架构）

**协议特点**:
- 传输层：TCP
- 数据格式：JSON（每行一条消息，以 `\n` 分隔）
- 连接模式：短连接（每次请求建立新连接，设备会在空闲几秒后自动断开）
- 默认端口：9100
- 实体定义：设备上报（`get_device` 命令返回实体列表）

---

## 连接参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 端口 | 9100 | 设备 TCP 监听端口 |
| 超时 | 3.0 秒 | 正常请求超时 |
| 扫描超时 | 0.3 秒 | 设备发现时的超时时间 |
| 轮询间隔 | 10 秒 | Home Assistant 状态更新频率 |

---

## 请求格式

所有请求均为单行 JSON 对象，以 `\n` 结尾。

### 获取设备信息和实体定义

```json
{"cmd":"get_device"}\n
```

**返回**: 设备基本信息和所有实体定义（`Wb2DeviceInfo`）。

### 获取实体状态

```json
{"cmd":"get_state"}\n
```

**返回**: 所有实体的当前状态（`Wb2State`，包含 `entities[]`）。

### 设置实体状态

```json
{"cmd":"set","id":"light_01","r":255,"g":0,"b":128}\n
{"cmd":"set","id":"switch_01","on":1}\n
{"cmd":"set","id":"light_01","brightness":128}\n
```

### 发送通用命令

```json
{"cmd":"pair"}\n
{"cmd":"reset"}\n
{"cmd":"calibrate"}\n
{"cmd":"restore"}\n
```

### 请求字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `cmd` | string | 是 | 命令类型：`get_device`、`get_state`、`set`、`pair`、`reset`、`calibrate`、`restore` |
| `id` | string | 否 | 目标实体 ID（`set` 命令必需） |
| `r` | int | 否 | 红色通道值 (0-255) |
| `g` | int | 否 | 绿色通道值 (0-255) |
| `b` | int | 否 | 蓝色通道值 (0-255) |
| `brightness` | int | 否 | 亮度值 (0-255) |
| `on` | int | 否 | 开关状态 (0=关闭, 1=打开) |

---

## 响应格式

### get_device 响应

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
  ],
  "offline_timeout": 300
}
```

> `offline_timeout`（秒，可选）：`>0` 时集成进入**推送-only 模式**（初始化后不轮询），
> 超过该时长未收到推送则实体变为不可用；`0`/缺省为轮询模式。设备仅在推送已配置时上报 `>0`。

### get_state 响应

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

### 响应字段说明

#### Wb2DeviceInfo（设备信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `mac` | string | 设备 MAC 地址 |
| `name` | string | 设备显示名称 |
| `model` | string | 设备型号 |
| `sw_version` | string | 固件版本 |
| `entities` | list | 实体定义列表 |
| `offline_timeout` | int | 掉线超时（秒，可选）：`>0` 启用推送-only 模式 |

#### Wb2EntityDef（实体定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 实体唯一标识符 |
| `type` | string | 实体类型（见下方类型表） |
| `name` | string | 实体显示名称 |
| `icon` | string | 图标 (MDI 图标名) |

#### Wb2State（状态响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| `state` | string | 设备状态（`online`/`offline`） |
| `entities` | list | 实体状态列表 |

#### Wb2EntityState（实体状态）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 实体 ID |
| `type` | string | 实体类型 |
| `data` | dict | 实体数据（类型相关） |

---

## 实体类型

| 类型 | 说明 | 数据字段 |
|------|------|----------|
| `light` | RGB LED 灯 | `r`, `g`, `b`, `brightness` |
| `switch` | 继电器开关 | `on` (0/1) |
| `binary_sensor` | 二进制传感器 | `motion`, `presence` (0/1) |
| `sensor` | 数据传感器 | `value` (字符串) |
| `event` | 事件实体 | `event_type`, `event_id` |

### light（RGB 灯）

支持功能：
- 颜色控制 (RGB)
- 亮度调节
- 开关控制

数据字段：`r`, `g`, `b`, `brightness`

### switch（继电器开关）

支持功能：
- 开关控制

数据字段：`on` (0=关闭, 1=打开)

### binary_sensor（二进制传感器）

支持功能：
- 存在检测
- 运动检测

数据字段：`motion`, `presence` (0=无, 1=有)

### sensor（数据传感器）

支持功能：
- 键值上报
- 其他数值型数据

数据字段：`value` (字符串)

### event（事件实体）

支持功能：
- 按键按下/释放事件
- 遥控器事件

事件类型：`press`, `release`

---

## 设备发现机制

Home Assistant 集成支持两种设备发现方式：

### Zeroconf / mDNS 自动发现

设备通过 mDNS 广播 `_and._tcp` 服务类型，Home Assistant 可自动发现局域网内的 AND 设备：

1. **服务类型**: `_and._tcp.local.`
2. **设备名称格式**: `and-{type}-{mac_suffix}` (如 `and-light-AABBCC`)
3. **发现流程**: 设备广播 → HA 自动识别 → 用户确认添加
4. **DNS 回退**: 连接失败时自动使用缓存 IP 地址

### TCP 扫描发现

如果 Zeroconf 发现失败，还可以通过 TCP 扫描发现设备：

1. **扫描范围**: 遍历所有本地网络接口，生成每个子网的 1-254 地址
2. **扫描端口**: 9100
3. **扫描方式**: 并发扫描（最多 64 个并发连接）
4. **扫描超时**: 每个设备 0.3 秒
5. **验证方法**: 发送 `{"cmd":"get_device"}` 命令，检查响应是否包含有效设备信息

如果自动发现失败，用户可以手动输入设备 IP 地址。

---

## 常量定义

```python
# 连接参数
DEFAULT_PORT = 9100
SCAN_TIMEOUT = 0.3  # 设备扫描超时（秒）
POLL_INTERVAL = 10  # 状态轮询间隔（秒），仅轮询模式
PUSH_CHECK_INTERVAL = 30  # 推送-only 模式的陈旧检查周期（秒，无网络 I/O）

# 设备类型
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_RADAR = "radar"
DEVICE_TYPE_EVENT = "event"
DEVICE_TYPE_KEY_SENSOR = "key_sensor"

# 默认值
DEFAULT_NAME = "Light"
DEFAULT_TYPE = "light"
DEFAULT_MODEL = "AND"
DEFAULT_SWITCH_COUNT = 3

# mDNS 服务类型
MDNS_SERVICE_TYPE = "_and._tcp"

# 配置键名
CONF_HOST = "host"
CONF_PORT = "port"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_TYPE = "type"
```

---

## 数据结构定义 (Python)

### Wb2DeviceInfo

```python
from dataclasses import dataclass, field

@dataclass
class Wb2EntityDef:
    """实体定义"""
    id: str
    type: str
    name: str = ""
    icon: str = ""
    action: str = ""

@dataclass
class Wb2DeviceInfo:
    """设备信息"""
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
    """单个实体状态"""
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
    """状态响应"""
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

## 代码示例

### Python 异步客户端

```python
import asyncio
import json

async def get_device_info(host: str, port: int = 9100):
    """获取设备信息和实体定义"""
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
    """获取所有实体状态"""
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
    """设置实体状态"""
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
    """发送通用命令"""
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

# 使用示例
async def main():
    host = "192.168.1.100"
    
    # 获取设备信息
    device_info = await get_device_info(host)
    print(f"设备: {device_info['model']} {device_info['name']}")
    print(f"实体数量: {len(device_info['entities'])}")
    
    # 获取状态
    states = await get_entity_states(host)
    for entity in states["entities"]:
        print(f"  {entity['id']}: {entity.get('data', {})}")
    
    # 设置灯颜色
    result = await set_entity_state(host, "light_01", {"r": 255, "g": 0, "b": 128})
    print(f"设置结果: {result}")
    
    # 打开开关
    result = await set_entity_state(host, "switch_01", {"on": 1})
    print(f"开关结果: {result}")
    
    # 校准雷达
    result = await send_command(host, "calibrate")
    print(f"校准结果: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### curl 测试命令

```bash
# 获取设备信息
echo '{"cmd":"get_device"}' | nc 192.168.1.100 9100

# 获取实体状态
echo '{"cmd":"get_state"}' | nc 192.168.1.100 9100

# 设置灯颜色
echo '{"cmd":"set","id":"light_01","r":255,"g":0,"b":128}' | nc 192.168.1.100 9100

# 设置亮度
echo '{"cmd":"set","id":"light_01","brightness":128}' | nc 192.168.1.100 9100

# 打开开关
echo '{"cmd":"set","id":"switch_01","on":1}' | nc 192.168.1.100 9100

# 433 配对
echo '{"cmd":"pair"}' | nc 192.168.1.100 9100

# 校准雷达
echo '{"cmd":"calibrate"}' | nc 192.168.1.100 9100
```

---

## 固件更新

### 更新方式

1. **串口更新**: 使用串口工具通过 UART 更新
2. **OTA 更新**: 通过网络进行无线更新（需固件支持）

### 更新步骤

1. 从安信可官方获取最新固件
2. 按照设备文档进行固件更新
3. 更新完成后设备自动重启
4. 在 Home Assistant 中重新添加设备

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 设备无法连接 | 检查 IP 地址、网络连接、防火墙设置 |
| 状态不同步 | 重启 Home Assistant，检查网络稳定性 |
| 扫描不到设备 | 确保在同一局域网，尝试手动添加 |
| 推送更新失败 | 检查 9101 端口是否被占用 |

## 相关链接

- [集成仓库 (GitHub)](https://github.com/AmateurNoobDog/and_home)
- [集成仓库 (Gitee)](https://gitee.com/AmateurNoobDog/and_home)
- [固件仓库 (GitHub)](https://github.com/AmateurNoobDog/wb2_ha_firmware)
- [固件仓库 (Gitee)](https://gitee.com/AmateurNoobDog/wb2_ha_firmware)
- [安信可官网](https://docs.ai-thinker.com/)
- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)

## 许可证

MIT License
