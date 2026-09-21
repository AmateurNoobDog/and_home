> **Language: [English](PROTOCOL_en.md) | 中文**

AND Home 是一个 Home Assistant 自定义集成，当前硬件平台为安信可（Ai-Thinker）WB2。

**固件开源地址**:
- 中国大陆: https://gitee.com/AmateurNoobDog/wb2_ha_firmware
- 中国港澳台及海外: https://github.com/AmateurNoobDog/wb2_ha_firmware

---

# AND Home 设备通信协议

## 概述

AND Home WB2 系列设备使用 **TCP Socket + JSON 行协议** 进行通信。

- **协议版本**: v2（实体驱动架构）
- **传输层**: TCP
- **数据格式**: JSON（每行一条消息，以 `\n` 分隔）
- **连接模式**: 短连接（每次请求建立新连接，设备空闲数秒后自动断开）
- **设备角色**: TCP 服务器
- **集成角色**: TCP 客户端

| 端口 | 用途 |
|------|------|
| 9100 | 设备 TCP 监听端口（集成主动连接） |
| 9101 | 推送端口（设备主动连接集成） |

---

## 设备发现

Home Assistant 集成支持三种方式发现设备：Zeroconf 自动发现、TCP 局域网扫描、手动输入。

### Zeroconf / mDNS 自动发现

设备启动后通过 mDNS 广播服务，Home Assistant 自动发现局域网内的设备。

**服务类型**: `_and._tcp.local.`

**设备名称格式**: `and-{type}-{mac_suffix}`

- `type`: 设备类型（如 `light`、`switch`）
- `mac_suffix`: MAC 地址后 6 位（大写）

**示例**:

假设设备 MAC 为 `AA:BB:CC:11:22:33`，设备类型为 `light`，则：

```
mDNS 服务名: and-light-AABBCC
mDNS 服务类型: _and._tcp.local.
端口: 9100
```

**发现流程**:

```
设备                          Home Assistant
  |                                |
  |--- mDNS 广播 ---------------->|  (服务类型: _and._tcp.local.)
  |                                |  解析名称: and-light-AABBCC
  |                                |  获取 IP 地址
  |<---- TCP 探测 (get_device) ---|  验证设备在线
  |---- 响应 (设备信息) --------->|
  |                                |  弹出确认对话框
  |<---- 用户确认添加 ------------|
  |                                |  创建配置项
```

### TCP 局域网扫描

当 Zeroconf 发现失败时，集成可通过 TCP 扫描发现设备。

**扫描参数**:

| 参数 | 值 | 说明 |
|------|-----|------|
| 扫描端口 | 9100 | 设备 TCP 监听端口 |
| 并发数 | 64 | 同时探测的主机数 |
| 单设备超时 | 0.3 秒 | 每个主机的探测超时 |
| 扫描范围 | 所有本地子网 | 遍历每个网口的 1-254 地址 |

**验证方法**: 向目标端口发送 `get_device` 命令，检查响应是否包含有效的 `mac` 字段。

**扫描请求示例**:

```json
{"cmd":"get_device"}\n
```

**有效响应示例**（设备存在）:

```json
{"mac":"AA:BB:CC:11:22:33","name":"客厅灯","model":"WB2-Light","entities":[]}
```

**无响应或无效响应**（设备不存在）:

- 连接超时
- 响应为空
- 响应 JSON 中无 `mac` 字段

### 手动输入

用户可手动输入设备的 IP 地址和端口号，集成会发送 `get_device` 命令验证设备是否在线。

**探测请求**:

```bash
echo '{"cmd":"get_device"}' | nc 192.168.1.100 9100
```

**有效响应**:

```json
{"mac":"AA:BB:CC:11:22:33","name":"客厅灯","model":"WB2-Light","sw_version":"1.0.0","entities":[{"id":"light_01","type":"light","name":"主灯","icon":"mdi:white-balance-sunny"}]}
```

**连接失败**: 无响应或超时，集成提示"无法连接到设备"。

---

## 设备信息上报 (get_device)

设备收到 `get_device` 命令后，返回设备基本信息和所有实体定义。集成在初始化和扫描探测时使用此命令。

### 请求格式

```json
{"cmd":"get_device"}\n
```

### 响应格式

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

### 字段说明

#### 设备信息字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `mac` | string | 是 | 设备 MAC 地址（格式 `AA:BB:CC:DD:EE:FF`） |
| `name` | string | 是 | 设备显示名称（如"客厅灯"） |
| `model` | string | 是 | 设备型号（如"WB2-Light"） |
| `manufacturer` | string | 否 | 制造商名称（如"Ai-Thinker"），不返回则不显示 |
| `sw_version` | string | 否 | 固件版本号 |
| `entities` | list | 是 | 实体定义列表 |

#### 实体定义字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 实体唯一标识符（如 `light_01`） |
| `type` | string | 是 | 实体类型（见下方类型表） |
| `name` | string | 否 | 实体显示名称 |
| `icon` | string | 否 | MDI 图标名（如 `mdi:power`） |
| `action` | string | 否 | 按钮动作命令（仅 `button` 类型使用） |

---

## 状态上报 (get_state)

设备收到 `get_state` 命令后，返回所有实体的当前状态。集成每 10 秒轮询一次。

### 请求格式

```json
{"cmd":"get_state"}\n
```

### 响应格式

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

### 字段说明

#### 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `state` | string | 设备状态：`online` 或 `offline` |
| `entities` | list | 实体状态列表 |

#### 实体状态字段

每个实体状态对象包含 `id` 和 `type` 字段，其余字段根据实体类型不同而不同。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 实体 ID（与 `get_device` 中的定义对应） |
| `type` | string | 实体类型 |
| 其他字段 | - | 类型相关的数据字段（见下方各类型说明） |

---

## 状态控制 (set)

集成向设备发送 `set` 命令来控制实体状态。

### 请求格式

```json
{"cmd":"set","id":"<实体ID>",...参数...}\n
```

### 各实体类型参数

#### light（RGB 灯）

| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `r` | int | 0-255 | 红色通道值 |
| `g` | int | 0-255 | 绿色通道值 |
| `b` | int | 0-255 | 蓝色通道值 |
| `brightness` | int | 0-255 | 亮度值 |

**设置灯颜色示例**:

```json
{"cmd":"set","id":"light_01","r":255,"g":0,"b":128}\n
```

**设置亮度示例**:

```json
{"cmd":"set","id":"light_01","brightness":128}\n
```

**关闭灯示例**（RGB 均为 0）:

```json
{"cmd":"set","id":"light_01","r":0,"g":0,"b":0}\n
```

#### switch（继电器开关）

| 参数 | 类型 | 值 | 说明 |
|------|------|-----|------|
| `on` | int | 0 或 1 | 0=关闭，1=打开 |

**打开开关示例**:

```json
{"cmd":"set","id":"switch_01","on":1}\n
```

**关闭开关示例**:

```json
{"cmd":"set","id":"switch_01","on":0}\n
```

#### number（数值控制）

| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `value` | int | 0-9 | 数值（如音量等级） |

**设置音量示例**:

```json
{"cmd":"set","id":"vol_01","value":7}\n
```

#### notify（TTS 播报）

| 参数 | 类型 | 说明 |
|------|------|------|
| `text` | string | 要播报的文本内容 |

**TTS 播报示例**:

```json
{"cmd":"set","id":"tts_01","cmd":"text","text":"欢迎回家"}\n
```

### set 响应

设备处理完 `set` 命令后，返回最新的完整状态（格式同 `get_state` 响应）。

```json
{
  "state": "online",
  "entities": [
    {"id": "light_01", "type": "light", "r": 255, "g": 0, "b": 128, "brightness": 200},
    {"id": "switch_01", "type": "switch", "on": 1}
  ]
}
```

集成收到响应后立即更新 HA 中的实体状态，无需等待下一次轮询。

---

## 通用命令

除了 `get_device`、`get_state`、`set` 外，设备还支持以下通用命令。

### pair（433 配对）

进入 433MHz 配对模式，等待接收遥控器信号。

```json
{"cmd":"pair"}\n
```

### reset（重启）

设备软重启。

```json
{"cmd":"reset"}\n
```

### calibrate（校准）

雷达传感器校准（如存在检测传感器）。

```json
{"cmd":"calibrate"}\n
```

### restore（恢复出厂）

恢复出厂设置。

```json
{"cmd":"restore"}\n
```

### 带实体 ID 的命令

部分命令可指定目标实体 ID：

```json
{"cmd":"pair","id":"event_01"}\n
```

### 通用命令响应

所有通用命令均返回最新完整状态（格式同 `get_state` 响应）。

---

## 推送上报 (TCP 9101)

除了集成轮询外，设备还可主动向集成推送状态变化。

### 工作机制

1. 集成启动时在 `0.0.0.0:9101` 启动 TCP 推送服务器
2. 设备状态变化时，主动连接集成的 9101 端口
3. 推送服务器通过 TCP 源 IP 匹配对应设备
4. 解析推送数据并更新 HA 实体状态

### 推送数据格式

设备推送的数据格式与 `get_state` 响应完全相同：

```json
{
  "state": "online",
  "entities": [
    {"id": "radar_01", "type": "binary_sensor", "motion": 1, "presence": 1},
    {"id": "event_01", "type": "event", "event_type": "press", "event_id": "btn_1"}
  ]
}
```

### 单实体推送格式

部分设备可能推送单个实体的状态（如 433 网关、按键传感器）：

```json
{"id": "event_01", "type": "event", "event_type": "press", "event_id": "btn_1"}
```

集成会自动识别此格式并转换为标准的 `Wb2State` 结构。

### 推送流程

```
设备                              Home Assistant
  |                                    |
  |--- TCP 连接 9101 ---------------->|
  |---- 推送数据 (JSON + \n) -------->|
  |                                    |  通过源 IP 匹配设备
  |                                    |  解析 Wb2State
  |                                    |  更新 HA 实体状态
  |<---- 连接关闭 --------------------|
```

### IP 匹配说明

推送服务器通过 TCP 连接的源 IP 地址匹配设备。集成在注册时会记录设备的 IP 地址（包括 Zeroconf 发现的 IP 和配置的 host）。

**注意**: 如果设备 IP 地址发生变化（如 DHCP 分配新 IP），推送将无法匹配到对应设备。此时轮询机制仍可正常工作。

---

## 请求/响应字段速查表

### 请求命令一览

| 命令 | 说明 | 必需字段 | 可选字段 |
|------|------|----------|----------|
| `get_device` | 获取设备信息和实体定义 | `cmd` | - |
| `get_state` | 获取所有实体状态 | `cmd` | - |
| `set` | 设置实体状态 | `cmd`, `id` | `r`, `g`, `b`, `brightness`, `on`, `value`, `text` |
| `pair` | 433 配对 | `cmd` | `id` |
| `reset` | 设备重启 | `cmd` | - |
| `calibrate` | 雷达校准 | `cmd` | - |
| `restore` | 恢复出厂 | `cmd` | - |

### 响应字段一览

#### get_device 响应

| 字段 | 类型 | 说明 |
|------|------|------|
| `mac` | string | 设备 MAC 地址 |
| `name` | string | 设备显示名称 |
| `model` | string | 设备型号 |
| `manufacturer` | string | 制造商（可选） |
| `sw_version` | string | 固件版本（可选） |
| `entities` | list | 实体定义列表 |

#### 实体定义字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 实体唯一标识符 |
| `type` | string | 实体类型 |
| `name` | string | 实体显示名称（可选） |
| `icon` | string | MDI 图标名（可选） |
| `action` | string | 按钮动作命令（仅 button 类型，可选） |

#### get_state / set / 推送响应

| 字段 | 类型 | 说明 |
|------|------|------|
| `state` | string | 设备状态：`online` / `offline` |
| `entities` | list | 实体状态列表 |

#### 实体状态字段（按类型）

**light**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `r` | int | 红色通道 (0-255) |
| `g` | int | 绿色通道 (0-255) |
| `b` | int | 蓝色通道 (0-255) |
| `brightness` | int | 亮度 (0-255) |

**switch**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `on` | int | 开关状态 (0=关, 1=开) |

**binary_sensor**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `motion` | int | 运动检测 (0=无, 1=有) |
| `presence` | int | 存在检测 (0=无, 1=有) |

**sensor**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `value` | string | 传感器数据值 |

**event**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `event_type` | string | 事件类型：`press` / `release` |
| `event_id` | string | 事件标识符 |

**number**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `value` | int | 数值 (0-9) |

---

## 实体类型总览

| 类型 | 说明 | 控制方式 | 数据字段 |
|------|------|----------|----------|
| `light` | RGB LED 灯 | set (r/g/b/brightness) | r, g, b, brightness |
| `switch` | 继电器开关 | set (on) | on |
| `binary_sensor` | 二进制传感器 | 仅上报 | motion, presence |
| `sensor` | 数据传感器 | 仅上报 | value |
| `event` | 事件实体 | 仅上报 | event_type, event_id |
| `button` | 按钮 | send_cmd (action) | - |
| `notify` | TTS 播报 | set (text) | - |
| `number` | 数值控制 | set (value) | value |

---

## 连接参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_PORT` | 9100 | 设备 TCP 监听端口 |
| `PUSH_PORT` | 9101 | 推送服务器端口 |
| 超时 | 3.0 秒 | 正常请求超时 |
| 扫描超时 | 0.3 秒 | 设备发现时的超时 |
| 轮询间隔 | 10 秒 | HA 状态更新频率 |
| 并发扫描数 | 64 | TCP 扫描最大并发连接 |
| 推送服务器重试 | 3 次 | 端口占用时重试次数 |
| 推送读取超时 | 5.0 秒 | 推送数据读取超时 |

---

## 完整通信示例

### 示例 1: 设备发现与初始化

```
1. 设备启动，mDNS 广播 _and._tcp.local. 服务
2. HA 发现设备，发送 get_device 验证

   >>> {"cmd":"get_device"}
   <<< {"mac":"AA:BB:CC:11:22:33","name":"客厅灯","model":"WB2-Light","manufacturer":"Ai-Thinker","sw_version":"1.0.0","entities":[{"id":"light_01","type":"light","name":"主灯","icon":"mdi:white-balance-sunny"},{"id":"switch_01","type":"switch","name":"开关1","icon":"mdi:power"}]}

3. 用户确认添加，HA 创建配置项
4. HA 首次轮询获取状态

   >>> {"cmd":"get_state"}
   <<< {"state":"online","entities":[{"id":"light_01","type":"light","r":255,"g":128,"b":64,"brightness":200},{"id":"switch_01","type":"switch","on":1}]}

5. HA 注册推送服务器，设备可主动推送状态变化
```

### 示例 2: 控制灯光

```
1. 用户在 HA 中打开灯并设置颜色

   >>> {"cmd":"set","id":"light_01","r":255,"g":0,"b":128,"brightness":200}
   <<< {"state":"online","entities":[{"id":"light_01","type":"light","r":255,"g":0,"b":128,"brightness":200},{"id":"switch_01","type":"switch","on":1}]}

2. 设备执行命令，返回最新状态
3. HA 立即更新实体状态（无需等待轮询）
```

### 示例 3: 推送上报

```
1. 遥控器按下按钮
2. 设备主动连接 HA 9101 端口

   >>> {"id":"event_01","type":"event","event_type":"press","event_id":"btn_1"}

3. HA 通过源 IP 匹配设备，更新实体状态
4. HA 触发相应自动化
```

### 示例 4: 雷达校准

```
1. 用户在 HA 中点击校准按钮

   >>> {"cmd":"calibrate","id":"radar_01"}
   <<< {"state":"online","entities":[{"id":"radar_01","type":"binary_sensor","motion":0,"presence":0}]}

2. 设备进入校准模式，返回当前状态
3. 校准完成后设备通过推送上报新状态
```
