# 给 Windows 上 AI agent 的诊断提示词（直接复制粘贴）

> 用法：把本文件全文粘给那台 Windows 机器上的 agent，它即可按步骤自查。包内已带 `hdc.exe` 与 `libusb_shared.dll`，无需联网。

---

你是这台 Windows 机器上的诊断助手。任务：定位"CPRO 设备通过 USB 连接本机，但 hdc 无法连接"的原因，并在证据充分时修复。全程优先只读，改动前先说明。

## 已知事实（已由另一台机器核实，不要重复推翻）

- CPRO 是 HarmonyOS/OpenHarmony 宿主（aarch64，内核 HongMeng 1.12.0），HDC 服务端是 `hdcd`；设备侧 persist 为 `persist.hdc.mode=tcp`、`persist.hdc.mode.usb=enable`、`persist.hdc.port=8710`。
- 设备 USB 身份：`USB\VID_12D1&PID_5000\0123456789ABCDEF`，友好名 `"HDC Device"`，USB 2.0 High-Speed。
- 在**另一台** Windows 上，同一台 CPRO 曾被成功枚举并配置（设备端 `UDC state=configured`、`[HIUSBC]hiusbc_gadget_pullup: is_on = 1`），且 `hdc -t 0123456789ABCDEF shell id` 返回 `uid=0(root)`。因此 CPRO 的 USB gadget 与线材本身可用，**本机问题在 Windows 驱动层或 hdc 层**。
- 正常绑定驱动是 Windows 自带 `winusb.inf`（服务 `WINUSB`，Provider `Microsoft`），通常无需安装厂商驱动。
- 本包自带客户端：`hdc_6.1.1.280\hdc.exe`，`Ver: 3.2.0d`；**必须与同目录 `libusb_shared.dll` 一起使用**，只拷 exe 会以 `0xC0000135` 退出。

## 执行步骤

1. 在包目录执行并保留证据：
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnose_usb_hdc.ps1 -OutFile .\evidence.txt`
2. 读 `evidence.txt`，逐段核对：
   - 第 2 段：`hdc -v` 是否为 `Ver: 3.2.0d`；`libusb` 是否为 `present`。
   - 第 3 段：是否出现 `VID_12D1` 节点；`present` 是否为 `True`；`ProblemCode`、`DriverInfPath`、`Service` 是什么。
   - 第 5 段：是否有**另一个** hdc 进程（DevEco Studio 等自带），8710 是否被占用。
   - 第 6 段：`list targets -v` 是空、`Offline`、`Unauthorized` 还是 `Connected`。
3. 按判定表处理（见下），每做一次改动就重跑第 1 步，记录前后差异。
4. 收尾给出结论：根因、已做改动、当前是否可用、证据文件路径。

## 判定表

| 证据 | 根因 | 允许的动作 |
|---|---|---|
| 无 `VID_12D1` 节点 | 本机未枚举（物理或端口） | 让操作者换数据线/换直连主板口/确认 CPRO 调试口；本机侧可 `pnputil /scan-devices` 重扫一次 |
| 有节点，`present=False` | 曾经枚举过、现在拔了 | 提示操作者插好线；不要据此判定"设备故障" |
| `ProblemCode` 28 或 43 | 无可用驱动/设备描述符失败 | 设备管理器卸载该设备（勾选删除驱动）→ 扫描硬件改动；若本机装过华为手机助手/HiSuite，先卸载其驱动包；仍失败再考虑安装 WinUSB 驱动 |
| 节点 `Status=OK`、`Service=WINUSB`，但 targets 空 | hdc 层 | `hdc kill` 一次 → `hdc list targets -v`；确认客户端版本 3.2.0d；停掉其它 hdc 进程后重试 |
| `Unauthorized` | 未授权 | 在 CPRO 侧接受授权后再试 |
| `0xC0000135` | 缺 DLL | 确保 `libusb_shared.dll` 与 `hdc.exe` 同目录 |

## 硬性边界（不要做）

- 不要执行 `hdc tmode`：会重启设备 `hdcd`，可能切断唯一可用通道。
- 不要向设备 `/config/usb_gadget/g1/UDC` 写空值：那是解绑 gadget。
- 不要改 CPRO 的 `eth0`、`ip rule` 或 `hdcrelay` 相关配置。
- 不要在没有明确说明的情况下删除/替换系统驱动、安装来源不明的驱动包。
- 不要为了"试试"反复插拔或重启设备；每次改动记录一条。

## 若本机同时有无线 HDC 目标

`hdc list targets -v` 可能出现两行（USB 与 `IP:port`）。此时所有命令必须带 `-t`：
`hdc -t 0123456789ABCDEF shell id`（USB）、`hdc -t <IP:port> shell id`（无线）。

## 交付物格式

```
结论：<一句话根因>
证据：evidence.txt 第 X 段显示 ...
已改动：<命令/操作，逐条>
当前状态：hdc list targets -v 输出原文
下一步：<仍需人工做的事>
```
