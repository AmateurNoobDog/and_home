# Ai-Thinker Home Assistant 集成

[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![license](https://img.shields.io/gitee/license/amateur-dog/ha_ai_thinker_home)](LICENSE)

用于控制 Ai-Thinker WB2 系列设备的 Home Assistant 自定义集成。

## 支持的设备

| 型号 | 类型 | 功能 |
|------|------|------|
| Ai-WB2-12F | Wi-Fi + BLE 模块 | RGB 灯、开关控制 |
| Ai-WB2-12S | Wi-Fi + BLE 模块 | RGB 灯、开关控制 |
| 其他 WB2 系列 | TCP + JSON 协议 | 根据固件支持 |

### 设备类型

- **wb2**: RGB LED 灯，支持颜色控制、亮度调节
- **sw**: 多通道继电器开关，最多 3 通道独立控制
- **radar**: 雷达传感器，支持存在检测和运动检测

## 安装方法

### 方法一：HACS 安装（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. 在 HACS 中点击右上角菜单 -> **自定义存储库**
3. 添加此仓库地址：
   ```
   https://gitee.com/amateur-dog/ha_ai_thinker_home
   ```
4. 选择类别为 **集成**
5. 点击安装
6. 重启 Home Assistant

### 方法二：手动安装

1. 下载此仓库的 `custom_components/ai_thinker_home` 文件夹
2. 复制到你的 Home Assistant 配置目录下的 `custom_components` 文件夹
3. 重启 Home Assistant

## 配置方法

### 自动发现

1. 进入 **设置** -> **设备与服务** -> **添加集成**
2. 搜索 "Ai-Thinker"
3. 集成将自动扫描局域网中的设备
4. 选择要添加的设备并完成配置

### 手动配置

如果自动发现失败：

1. 选择 "手动输入 IP 地址"
2. 输入设备 IP 地址（端口默认 9100）
3. 点击提交

## 通信协议

设备使用 TCP + JSON 行协议通信：

- **端口**: 9100
- **格式**: JSON，以 `\n` 分隔
- **连接**: 短连接（设备空闲后自动断开）

### 命令示例

```bash
# 获取设备状态
echo '{"cmd":"get"}' | nc 192.168.1.100 9100

# 设置 RGB 颜色
echo '{"cmd":"set","r":255,"g":0,"b":128}' | nc 192.168.1.100 9100

# 控制继电器
echo '{"cmd":"set","on":1,"channel":0}' | nc 192.168.1.100 9100
```

## 固件更新

### 更新方式

1. **串口更新**: 使用串口工具通过 UART 更新
2. **OTA 更新**: 通过网络进行无线更新（需固件支持）

### 更新步骤

1. 从 Ai-Thinker 官方获取最新固件
2. 按照设备文档进行固件更新
3. 更新完成后设备自动重启
4. 在 Home Assistant 中重新添加设备

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 设备无法连接 | 检查 IP 地址、网络连接、防火墙设置 |
| 状态不同步 | 重启 Home Assistant，检查网络稳定性 |
| 扫描不到设备 | 确保在同一局域网，尝试手动添加 |

## 相关链接

- [Ai-Thinker 官网](https://www.ai-thinker.com/)
- [Home Assistant](https://www.home-assistant.io/)
- [HACS](https://hacs.xyz/)

## 许可证

MIT License
