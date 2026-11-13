# 2026-11-11 11:45 USB HDC 当前状态只读复核

本阶段只做 Windows PnP/HDC 与 CPRO gadget 状态读取；未修改 CPRO 配置，未重启/停止任何服务，未动 `eth0`、`ip rule` 或 `hdcrelay`，无机器人动作。

## Windows / HDC

```text
USB target                         Offline
192.168.10.180:10178 TCP target   Connected
192.168.10.180:8710  TCP target   Offline
Get-PnpDevice -PresentOnly | InstanceId 匹配 VID_12D1
（无结果）
Test-NetConnection 192.168.10.180:10178 = True
```

## CPRO gadget（经现有 WiFi HDC 只读查询）

```text
UDC=ea100000.hiusbc
STATE=not attached
SPEED=high-speed
F1=../../../../usb_gadget/g1/functions/ffs.hdc
EXTCON=USB=1,USB-HOST=0
hdcrelay 192.168.10.180:10178 -> 127.0.0.1:8710 仍在运行
```

## 判断

- 10:24 的确定性软件故障（`configs/b.1/f1` 缺失、bind 返回 `-22`）当前没有复发：`f1` 与 `UDC` 均在位。
- Windows 连 `VID_12D1` PnP 设备都看不到，故当前失败发生在 HDC/WinUSB 之前的 USB attach/枚举层；反复安装驱动或切换 HDC 模式不能解决这一层。
- 本固件的 `extcon`、`current_speed` 在拔线后会保留旧值，不能用来证明 VBUS/数据线当前真实连接；以 Windows PnP 为准。
- WiFi 化没有排他地关闭 USB：历史上 `persist.hdc.mode.usb=enable`，且 USB/TCP 双 target 曾同时 Connected。当前更像主机 USB-C 端口/角色状态、线或接口接触的间歇性问题；若在此前成功的另一台 Windows 上仍能枚举，则主工作站 USB-C 口/控制器优先；若多台主机均不能枚举，再优先查线与 CPRO USB-A 母座。

