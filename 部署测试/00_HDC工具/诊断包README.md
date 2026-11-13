# CPRO USB HDC 诊断包

给"CPRO 通过 USB 连到这台 Windows，但 hdc 连不上"的场景用。包内所有东西都是现成的，解压即用。

## 三步用法

```powershell
# 1) 解压后进入目录，跑自检（只读，不装驱动、不杀进程），并把证据存成文件
powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnose_usb_hdc.ps1 -OutFile .\evidence.txt

# 2) 用包内自带的 hdc 复测（注意是 6.1.1.280 这个版本）
.\hdc_6.1.1.280\hdc.exe -v
.\hdc_6.1.1.280\hdc.exe list targets -v

# 3) 把 evidence.txt 和上面两条的输出回传
```

## 目录内容

| 文件 | 用途 |
|---|---|
| `diagnose_usb_hdc.ps1` | 只读自检：系统版本、hdc 版本与哈希、`VID_12D1` 设备节点及驱动、异常设备、hdc 进程与 8710 端口、targets |
| `hdc_6.1.1.280/hdc.exe` | HDC 客户端（`Ver: 3.2.0d`），与 CPRO 侧 `hdcd` 配套 |
| `hdc_6.1.1.280/libusb_shared.dll` | **必需**，hdc.exe 的 PE 导入表依赖它 |
| `AGENT_PROMPT.md` | 直接粘贴给这台机器上 AI agent 的提示词 |
| `reference_expected.txt` | 一台已知可用机器上的关键特征，用于对照 |

## 关键提醒

1. **`hdc.exe` 和 `libusb_shared.dll` 必须在同一目录**。只拷 exe 会 `0xC0000135`，表现就是"连不上"。
2. 目标设备特征：`USB\VID_12D1&PID_5000\0123456789ABCDEF`，设备名 `"HDC Device"`，正常时驱动为 Windows 自带 `winusb.inf / WINUSB`（无需装华为专用驱动）。
3. 判断"连上没连上"**只认本机 Windows 枚举**：`Get-PnpDevice` 里有 `VID_12D1` 且 `Status=OK`，并且 `hdc list targets -v` 里该行是 `Connected`。
4. 若同时有 USB 和无线两个目标（无线当前为 `192.168.10.180:8710`，旧中继 `10178` 已停用），所有 hdc 命令必须带 `-t`。
5. 不要在排查中执行 `hdc tmode`，也不要向设备 `/config/usb_gadget/g1/UDC` 写空值——那会解绑 USB gadget。

## 常见结论速查

| 现象 | 结论 | 处理 |
|---|---|---|
| 无任何 `VID_12D1` 节点 | 物理层没通 | 换数据线、直连主板 USB 口、确认插的是 CPRO 的调试口 |
| 有节点但 `ProblemCode` 28 / 43 | 驱动没绑上或被抢 | 设备管理器卸载设备（勾删除驱动）→ 扫描硬件改动；先卸华为手机助手/HiSuite |
| 节点正常但 targets 空 | hdc 层 | `hdc kill` 后重跑；确认 `hdc -v` 为 `3.2.0d`；停掉 DevEco 自带的另一个 hdc |
| 报 `0xC0000135` | 缺 DLL | 拷齐 `libusb_shared.dll` |
| targets 为 `Unauthorized` | 未授权 | 在设备侧接受授权 |
