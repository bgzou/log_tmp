# 2026-11-11 11:57 CPRO 正确 HDC 物理口确认

用户将线换到另一个 CPRO USB 口后，经现有 WiFi HDC 只读检查。未修改设备配置、网络或服务，无机器人动作。

## 结果

```text
2026-11-11 11:57:19 +08:00
STATE=configured
SPEED=high-speed
UDC=ea100000.hiusbc
F1=../../../../usb_gadget/g1/functions/ffs.hdc
```

新内核事件：

```text
hiusbc_dev_event_reset
hiusbc_dev_event_connect: Connected at speed = 3
usb_gadget_work: current usb state is CONNECTED
hiusbc_req_set_config: usbcore Set Configuration success
usb_gadget_work: current usb state is CONFIGURED
```

## 结论

- 当前所插 CPRO 物理口就是 `hiusb-port0 / ea100000.hiusbc` 对应的正确 HDC device-mode 口。
- CPRO 到第二台 Windows 的物理链路、USB 枚举和配置均已成功；若第二台 Windows 的 `hdc` 仍看不到设备，后续故障范围只剩该 Windows 的 WinUSB/HDC 客户端层。
- 应现场标记该 CPRO 口，避免以后误插其余 host-mode USB 口。

