# Ai-Thinker WB2 设备通信协议文档

## 概述

Ai-Thinker WB2 系列设备使用 **TCP Socket + JSON 行协议** 进行通信。设备作为 TCP 服务器，Home Assistant 集成作为客户端连接设备并发送命令。

**协议特点**:
- 传输层：TCP
- 数据格式：JSON（每行一条消息，以 `\n` 分隔）
- 连接模式：短连接（每次请求建立新连接，设备会在空闲几秒后自动断开）
- 默认端口：9100

---

## 连接参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 端口 | 9100 | 设备 TCP 监听端口 |
| 超时 | 3.0 秒 | 正常请求超时 |
| 扫描超时 | 0.3 秒 | 设备发现时的超时时间 |
| 轮询间隔 | 3 秒 | Home Assistant 状态更新频率 |

---

## 请求格式

所有请求均为单行 JSON 对象，以 `\n` 结尾。

### 获取设备状态

```json
{"cmd":"get"}\n
```

**返回**: 设备的完整状态信息。

### 设置设备状态

**设置 RGB 颜色** (适用于 RGB 灯设备):

```json
{"cmd":"set","r":255,"g":0,"b":128}\n
```

**控制继电器开关** (适用于开关设备):

```json
{"cmd":"set","on":1,"channel":0}\n
{"cmd":"set","on":0,"channel":1}\n
```

**混合控制**:

```json
{"cmd":"set","r":255,"g":255,"b":255,"on":1,"channel":0}\n
```

### 请求字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `cmd` | string | 是 | 命令类型：`"get"` 或 `"set"` |
| `r` | int | 否 | 红色通道值 (0-255) |
| `g` | int | 否 | 绿色通道值 (0-255) |
| `b` | int | 否 | 蓝色通道值 (0-255) |
| `on` | int | 否 | 通道 0 开关状态 (0=关闭, 1=打开) |
| `on1` | int | 否 | 通道 1 开关状态 (0=关闭, 1=打开) |
| `on2` | int | 否 | 通道 2 开关状态 (0=关闭, 1=打开) |
| `channel` | int | 否 | 指定要控制的通道号 (默认 0) |

---

## 响应格式

响应为单行 JSON 对象，包含设备的当前状态。

### 完整响应示例

```json
{"r":255,"g":128,"b":64,"on":1,"on1":0,"on2":1,"motion":0,"count":3,"mac":"AA:BB:CC:DD:EE:FF","type":"wb2","name":"客厅灯","model":"Ai-Thinker","names":["主灯","氛围灯","射灯"]}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `r` | int | 红色通道当前值 (0-255)，默认 0 |
| `g` | int | 绿色通道当前值 (0-255)，默认 0 |
| `b` | int | 蓝色通道当前值 (0-255)，默认 0 |
| `on` | int/None | 通道 0 开关状态 (0 或 1) |
| `on1` | int/None | 通道 1 开关状态 (0 或 1) |
| `on2` | int/None | 通道 2 开关状态 (0 或 1) |
| `motion` | int/None | 运动检测标志 (0=无运动, 1=检测到运动) |
| `count` | int/None | 继电器通道数量 |
| `mac` | string/None | 设备 MAC 地址 |
| `type` | string/None | 设备类型 (见下方设备类型) |
| `name` | string/None | 设备显示名称 |
| `model` | string/None | 设备型号 |
| `names` | list/None | 各通道名称列表 |

### 设备验证逻辑

设备响应必须满足以下条件之一才会被识别为有效的 WB2 设备：

1. 同时包含 `r`、`g`、`b` 三个字段 (RGB 灯)
2. 包含 `on` 字段 (继电器开关)
3. 包含 `motion` 字段 (雷达传感器)

---

## 设备类型

| 类型代码 | 常量名 | Home Assistant 平台 | 说明 |
|----------|--------|---------------------|------|
| `wb2` | `DEVICE_TYPE_LIGHT` | `light` | RGB LED 灯，支持颜色控制 |
| `sw` | `DEVICE_TYPE_SWITCH` | `switch` | 多通道继电器开关，支持独立控制 |
| `radar` | `DEVICE_TYPE_RADAR` | `binary_sensor` | 雷达存在/运动检测传感器 |

### wb2 (RGB 灯)

支持功能：
- 颜色控制 (RGB)
- 亮度调节
- 开关控制

支持字段：`r`, `g`, `b`, `on`

### sw (继电器开关)

支持功能：
- 多通道独立开关控制
- 支持最多 3 个通道 (on, on1, on2)

支持字段：`on`, `on1`, `on2`, `count`, `names`

### radar (雷达传感器)

支持功能：
- 存在检测
- 运动检测

支持字段：`motion`

---

## 设备发现机制

Home Assistant 集成支持局域网自动扫描发现设备：

1. **扫描范围**: 遍历所有本地网络接口，生成每个子网的 1-254 地址
2. **扫描端口**: 9100
3. **扫描方式**: 并发扫描（最多 64 个并发连接）
4. **扫描超时**: 每个设备 0.3 秒
5. **验证方法**: 发送 `{"cmd":"get"}` 命令，检查响应是否包含有效设备标识

如果扫描失败，用户可以手动输入设备 IP 地址。

---

## 常量定义

```python
# 连接参数
DEFAULT_PORT = 9100
SCAN_TIMEOUT = 0.3  # 设备扫描超时（秒）
POLL_INTERVAL = 3   # 状态轮询间隔（秒）

# 设备类型
DEVICE_TYPE_LIGHT = "wb2"
DEVICE_TYPE_SWITCH = "sw"
DEVICE_TYPE_RADAR = "radar"

# 默认值
DEFAULT_NAME = "Light"
DEFAULT_TYPE = "wb2"
DEFAULT_MODEL = "Ai-Thinker"
DEFAULT_SWITCH_COUNT = 3

# 配置键名
CONF_HOST = "host"
CONF_PORT = "port"
CONF_DEVICE_NAME = "device_name"
CONF_MAC = "mac"
CONF_TYPE = "type"
```

---

## 数据结构定义 (Python)

### Wb2State

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Wb2State:
    """设备状态数据结构"""
    r: int = 0
    g: int = 0
    b: int = 0
    on: Optional[int] = None
    on1: Optional[int] = None
    on2: Optional[int] = None
    motion: Optional[int] = None
    count: Optional[int] = None
    mac: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    names: Optional[List[str]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Wb2State":
        """从字典创建 Wb2State 实例"""
        names = data.get("names")
        return cls(
            r=int(data.get("r", 0)),
            g=int(data.get("g", 0)),
            b=int(data.get("b", 0)),
            on=int(data["on"]) if "on" in data else None,
            on1=int(data["on1"]) if "on1" in data else None,
            on2=int(data["on2"]) if "on2" in data else None,
            motion=int(data["motion"]) if "motion" in data else None,
            count=int(data["count"]) if "count" in data else None,
            mac=data.get("mac"),
            type=data.get("type"),
            name=data.get("name"),
            model=data.get("model"),
            names=names if isinstance(names, list) else None,
        )

    def channel_state(self, channel: int) -> Optional[int]:
        """获取指定通道的开关状态"""
        if channel == 0:
            return self.on
        return getattr(self, f"on{channel}", None)
```

---

## 代码示例

### Python 异步客户端

```python
import asyncio
import json

async def get_device_state(host: str, port: int = 9100):
    """获取设备状态"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        # 发送 get 命令
        writer.write(b'{"cmd":"get"}\n')
        await writer.drain()
        
        # 读取响应
        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        if line:
            data = json.loads(line.decode())
            return data
    finally:
        writer.close()
        await writer.wait_closed()

async def set_rgb_color(host: str, r: int, g: int, b: int, port: int = 9100):
    """设置 RGB 颜色"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        cmd = {"cmd": "set", "r": r, "g": g, "b": b}
        writer.write((json.dumps(cmd) + "\n").encode())
        await writer.drain()
        
        line = await asyncio.wait_for(reader.readline(), timeout=3.0)
        if line:
            return json.loads(line.decode())
    finally:
        writer.close()
        await writer.wait_closed()

async def set_relay(host: str, channel: int, on: bool, port: int = 9100):
    """控制继电器开关"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        cmd = {"cmd": "set", "on": int(on), "channel": channel}
        writer.write((json.dumps(cmd) + "\n").encode())
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
    
    # 获取状态
    state = await get_device_state(host)
    print(f"设备状态: {state}")
    
    # 设置 RGB 颜色为白色
    result = await set_rgb_color(host, 255, 255, 255)
    print(f"设置结果: {result}")
    
    # 打开继电器通道 0
    result = await set_relay(host, 0, True)
    print(f"开关结果: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### curl 测试命令

```bash
# 获取设备状态
echo '{"cmd":"get"}' | nc 192.168.1.100 9100

# 设置 RGB 颜色
echo '{"cmd":"set","r":255,"g":0,"b":128}' | nc 192.168.1.100 9100

# 控制继电器
echo '{"cmd":"set","on":1,"channel":0}' | nc 192.168.1.100 9100
```

---

## 注意事项

1. **短连接**: 设备会在空闲几秒后自动断开连接，不要复用连接
2. **并发控制**: 建议使用锁机制避免多个请求并发发送
3. **超时处理**: 正常请求超时为 3 秒，设备扫描超时为 0.3 秒
4. **JSON 格式**: 请求和响应都必须是有效的 JSON 格式，以 `\n` 结尾
5. **字段可选性**: 响应中的字段是可选的，需要处理 `None` 值情况

---

## 版本信息

- 文档版本: 1.0
- 适用固件: Ai-Thinker WB2 系列
- 协议版本: JSON Line Protocol
- 最后更新: 2026-09-02
