# 2026-11-11 11:51–11:52 第二台 Windows 接线后的 USB 只读检查

用户将 CPRO USB 线移到另一台 Windows。本聊天仍运行于工作站 `bgzou9897`，无法直接读取第二台 Windows 的 PnP 数据，因此经现有 WiFi HDC 从 CPRO 侧检查 USB gadget 是否完成 attach。全程只读；没有修改 CPRO 配置、服务或网络，无机器人动作。

## 工作站侧

```text
USB target                         Offline
192.168.10.180:10178 TCP target   Connected
Get-PnpDevice 当前无 VID_12D1/HDC Device
```

这符合 USB 线已从工作站移走，不能用于判断第二台 Windows 自身的 PnP 状态。

## CPRO 侧（11:52，经 WiFi 只读）

```text
UDC=ea100000.hiusbc
STATE=not attached
SPEED=high-speed
F1=../../../../usb_gadget/g1/functions/ffs.hdc
USB_UDC_NAME=hiusbc-gadget
USB_UDC_DRIVER=g1
```

内核日志中最后一次真实 HIUSBC pull-up/bind 仍是此前手工修复：

```text
[415542.739847] hiusbc_gadget_pullup: is_on = 1
```

在第二台 Windows 插线后的当前时间段，没有新的 HIUSBC attach/configured/枚举事件。日志还证实 `chipset_init` 的标准 USB 重建流程会删除并重建 `configs/b.1/f1`，而当前 `f1` 已正常存在。

## 判断

- 第二台 Windows 接线后 CPRO 仍为 `not attached`，没有完成 USB attach；不是 HDC target 选择或 WinUSB 上层问题。
- 因两台主机均未触发枚举，原工作站 USB-C 口不再是首要嫌疑。优先级转为：数据线/接头间歇故障、CPRO USB-A 母座接触问题、CPRO USB device 控制器卡住。
- 下一步先换一根已知支持数据的线并更换第二台 Windows 的物理 USB 口；仍无枚举再检查 CPRO 母座。保持 WiFi HDC，不执行 CPRO 重启、`hdc tmode` 或 UDC 空写。

