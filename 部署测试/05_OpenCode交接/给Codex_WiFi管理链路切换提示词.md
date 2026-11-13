# 给 Codex：CPRO 管理链路已切换 WiFi（2026-11-09 19:53，USB 已拔）

> **2026-11-11 20:46 勘误（本文其余内容仅作历史）：**“8710 只接受 lo 连接、必须靠 hdcrelay 中继”的说法已不成立于当前固件状态。CPRO 20:41 重启后，`hdcd` 直接监听 `0.0.0.0:8710`，`hdc tconn 192.168.10.180:8710` 即可用，无需中继；重启也不需要再插 USB 起中继。现行规则见 `部署测试/AGENTS.md` 末尾「管理链路」节与 `02_现场操作/实机事实与命令.md`。

**背景**：服务器 OpenCode 刚完成 PC↔CPRO 管理链的 WiFi 化改造并全项验收，USB 线已从工作站拔除。你的 FSM/实机工作流程不受影响，所有 hdc 用法保持不变，只多一个连接步骤。本提示词自包含，读完即可操作。

## 链路事实（均已实测验证）

- 工作站（你所在）：wifi-x，IP 192.168.10.61
- CPRO：wlan0 192.168.10.180（wifi-x）；eth0 192.168.123.100/24 机器人有线链**不变**
- 这台 CPRO 固件的 hdcd TCP 监听（8710）只接受从 lo 接口进入的连接（厂商安全加固，外部直连被静默丢弃），因此设备上跑着常驻原生中继 `hdcrelay`：监听 `192.168.10.180:10178` → 转发 `127.0.0.1:8710`
- 设备端已 persist：`persist.hdc.mode=tcp`、`persist.hdc.port=8710`、`persist.hdc.mode.usb=enable`（USB 随时可插回，不受影响）

## 怎么连（只在 hdc 服务器重启后才需要）

```powershell
& "D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\00_HDC工具\hdc_6.1.1.280\hdc.exe" tconn 192.168.10.180:10178
& "D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\00_HDC工具\hdc_6.1.1.280\hdc.exe" list targets
```

tconn 应显示 `Connect OK`；list targets 应显示 `192.168.10.180:10178`。**当前这个 tconn 已替你连好**，由 Windows 的 hdc 后台服务器进程保持——只要不执行 `hdc kill`、不重启 Windows，就一直有效，无需重连。命令异常时先 `list targets` 检查，目标丢了就重跑上面的 tconn。

连上之后，所有命令（`shell`、`file send`、`file recv`、`现场入口.ps1` 的 Sync/SdkBuild 等阶段）与 USB 时代**完全一致**，单目标时不需要 `-t`。

## 使用规则

1. 若把 USB 线插回：出现两个目标，此时所有命令必须加 `-t 192.168.10.180:10178`（走 WiFi）或 `-t <USB 目标键>`（走 USB）。
2. `hdc file send` 的本机源路径必须是**绝对路径**（既有已知问题，相对路径会在远端创建错误目录树）。
3. ping CPRO 不通是正常的（两端系统都不回 ICMP）。测连通性用 TCP：`Test-NetConnection 192.168.10.180 -Port 10178`。
4. **不要执行任何 `tmode` 命令**（链路已配置好，动它会破坏当前状态）；不要动 CPRO 的 eth0 配置和 ip rule（机器人链路）。

## 故障恢复

- **tconn 失败/目标消失，且 CPRO 刚重启过**：hdcrelay 不随设备重启存活。恢复步骤：
  1. 把 USB 线插回工作站；
  2. `hdc shell "unshare --uts --fork /data/local/tmp/as2w_field/hdcrelay 192.168.10.180 10178 127.0.0.1:8710"`（`unshare --uts --fork` 是必需的：宿主 UTS 视图报内核 1.12.0，静态二进制直接跑会 `FATAL: kernel too old`）；
  3. 确认 `hdc shell "netstat -tln | grep 10178"` 有 LISTEN；
  4. 重新 tconn，然后可以再拔线。
- **CPRO 的 wlan IP 变了**（当前租约 forever，但 DHCP 理论上可能变）：用新 IP 替换 tconn 目标与 hdcrelay 启动参数。
- 中继日志在设备 `/data/local/tmp/as2w_field/hdcrelay.log`；`hdc shell "pidof hdcrelay"` 查进程是否存活。

## 安全

10178 中继等于把 CPRO 的**无认证 root shell** 暴露给 wifi-x 全网段。仅限当前受信网络使用；如果长期只用 USB，可 `hdc shell "pkill hdcrelay"` 关闭中继。

## 记录

涉及此链路的操作或异常，按项目规则记入 `部署测试/04_调试记录/INDEX.md`。本次改造的完整技术记录：`部署测试/04_调试记录/logs/20261109-1952_opencode_wifi_hdc_link.md`。其余安全门槛（禁止真机 LowCmd、任何可能使狗动作的命令须先获现场人员当次明确同意等）见项目 AGENTS.md，全部不变。
