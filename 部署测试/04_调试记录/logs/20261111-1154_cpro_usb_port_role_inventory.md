# 2026-11-11 11:53–11:54 CPRO USB 端口角色只读核验

用户同时更换了 CPRO 物理 USB 口和第二台 Windows 物理口。经 WiFi HDC 只读检查，无设备配置修改、无机器人动作。

## 当前状态

```text
UDC=ea100000.hiusbc
state=not attached
f1=../../../../usb_gadget/g1/functions/ffs.hdc
```

换口后没有新增 HIUSBC attach/configured 事件。

## 端口角色

`/sys/class/udc` 只暴露一个 USB device controller：

```text
ea100000.hiusbc
  -> /sys/devices/platform/hiusb/hiusb_port/hiusb-port0/ea100000.hiusbc/udc/ea100000.hiusbc
```

extcon 角色：

```text
extcon0 hisi_usb2_0  USB=0 USB-HOST=1
extcon1 hisi_usb3_0  USB=1 USB-HOST=0
extcon2 hisi_usb3_1  USB=0 USB-HOST=1
extcon3 hisi_usb3_2  USB=0 USB-HOST=1
extcon4 hisi_usb3_3  USB=0 USB-HOST=1
```

## 判断

- HDC gadget 只绑定 `hiusb-port0/ea100000.hiusbc` 对应的唯一 device-mode 物理口；其余端口当前是 host-mode，不能通过换插直接枚举为 Windows HDC 设备。
- 同时更换 CPRO 口使前一轮“换主机端口”实验失去可比性。应立即断开当前非确认端口，改回 10:29 曾成功枚举的 CPRO 原口；只更换 Windows 端口/线材，再观察 `state` 是否变为 `configured`。
- 不修改其他端口角色，不尝试把 host 口强制切 device；保持 WiFi 管理链。

