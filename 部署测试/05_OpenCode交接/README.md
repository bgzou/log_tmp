# 从服务器 OpenCode 接续本机 AS2-W 项目

**2026-11-13 网络地址变更（先看这条）：**caolin 服务器地址随所在网络变动，**当前（17:08 恢复挂载时）为 `caolin@192.168.10.13`、工作站 WLAN `192.168.10.34`**；当天下午曾在 `192.168.43.12` / `192.168.43.4`（旧网段为 192.168.10.163 / 192.168.10.61）。两次都已把 `/home/caolin/as2w_workstation` 挂回 `zoubu@<工作站当前IP>:/D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO`，读写验证通过。前提是工作站 sshd 在跑且防火墙规则 `AS2W-OpenCode-Workstation-SSH` 的 `RemoteAddress` 含当前服务器 IP（现为 `192.168.10.163,192.168.43.12,192.168.10.13`）；只改 IP 不改这条规则时，表现是服务器→工作站 SSH 超时。下方命令中的旧 IP 请按当前网段替换，其余步骤不变。原始记录见 `../04_调试记录/INDEX.md` 2026-11-13 15:34–15:40 与 17:05–17:10 两节。

**2026-11-12 当前 R1199 任务：**用户已确认旧版两次实机抖动/停走跳变，不再复演旧故障。caolin OpenCode 请使用 `给OpenCode_R1199首条Prompt_20261112.md`，完整任务书 `给OpenCode_R1199训练合同修复与明日实机接续_20261112.md`。源码已有默认关闭的训练合同候选，尚未编译/仿真/同步CPRO；旧 joystick 入口阻断。只有同事训练服务器今晚可访问，caolin/CPRO 明天到实验室后再做其余工作。下文 R214 提示词均为历史阶段入口。

**2026-11-11 20:46 管理链更新（先看这条）：**无线 HDC 已改为**直连** `192.168.10.180:8710`。CPRO 于 20:41 重启后、在未启动 `hdcrelay` 的情况下，实测 `hdcd` 监听 `0.0.0.0:8710`，`hdc tconn 192.168.10.180:8710` → `Connect OK`、root shell 正常。因此“重启后必须插 USB 起中继”的旧流程作废；`10178` 中继仅作回退。本机（工作站）重启后只需重跑 `tconn`。USB 也在同次重启后自动恢复。下文涉及 `10178` 的段落均按此条理解。

**2026-11-11 现行交接：**粘贴 `给OpenCode_R214最小安全壳首条Prompt_20261111.md` 全文；详细任务书是 `给OpenCode_R214最小安全壳接续_20261111.md`。R214 已加入低速早期 bring-up 的命令斜率、遥控格式/超时、dq/tau_est/预计PD力矩/目标跳变两级守卫；x86 与 CPRO 三构建已通过，但新阈值尚未真机验收。OpenCode 首先只做 P0–P2 的代码审查、离线故障注入和文档，不自行 ReleaseMode/LowCmd。下文 2026-11-10 交接为历史背景。

**2026-11-10 现行交接：**运行OpenCode后，粘贴 `给OpenCode_R214_B策略首条Prompt_20261110.md` 全文；详细任务书是 `给OpenCode_R214_B策略接续_20261110.md`。已完成修复版A固定PD站立与Y受控趴下真机验收，B/策略尚未实机测试。先验证SSHFS，严格执行每次动作单独告知和当次许可。下文2026-11-09 R152/R214提示词均为历史。

**当前 R214 主线（2026-11-09 晚间）：**启动 OpenCode 后，请发送“请先通读并执行 `部署测试/05_OpenCode交接/给OpenCode_R214_FSM增益续作提示词.md`；项目根、日志和源码均在当前 SSHFS 挂载的工作站目录”。该提示词覆盖下文旧 R152 首条任务书。先确认 `mountpoint -q ~/as2w_workstation`；当前 CPRO 管理链走 WiFi HDC，详根 AGENTS 和 INDEX 最新节。

## 已核实的连接

2026-11-09：Windows 工作站 WLAN 是 `192.168.10.61`，服务器是 `192.168.10.163`。双向 SSH 已实测；服务器 Ubuntu 24.04.4、`opencode 1.18.18` 可运行，`sshfs 3.7.3` 已安装。服务器的专用私钥只在 `~/.ssh/as2w_workstation`，本目录仅存对应公钥。服务器已将工作站项目挂载到 `/home/caolin/as2w_workstation`；从服务器调用 Windows `GetState` 经 HDC 返回 `ai_damping`，日志写入工作站。

## 一次性开通工作站 SSH

在**工作站本机的管理员 PowerShell**运行：

```powershell
powershell.exe -ExecutionPolicy Bypass -File 'D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\05_OpenCode交接\启用工作站SSH.ps1'
```

脚本已由现场人员在管理员 PowerShell 执行成功：安装 Windows OpenSSH Server，把服务器公钥加入管理员账号的 SSH 授权文件，启动 `sshd`，并只允许 `192.168.10.163` 入站 TCP/22；另把无中文路径的只读阶段启动器复制到 `C:\Users\zoubu\as2w_field.ps1`。安装日志在 `部署测试/04_调试记录/logs/20261109-104250_workstation_ssh_setup.log`。不会把服务器账号密码写入文件；重启后若连接断开，先查 `sshd` 服务与工作站 WLAN 地址。

## 在服务器上挂载工作站项目

**现行地址（2026-11-13）：**服务器 `192.168.43.12`、工作站 `zoubu@192.168.43.4`；下面示例里的旧地址 `192.168.10.163` / `192.168.10.61` 直接替换即可，`/D:/...` SFTP 路径与专用密钥不变。挂载前先 `fusermount3 -u ~/as2w_workstation` 清掉 stale 挂载，并确认工作站防火墙 `AS2W-OpenCode-Workstation-SSH` 的 `RemoteAddress` 含当前服务器 IP（否则表现为 ssh 超时）。

先在工作站终端 `ssh caolin@192.168.10.163`，密码只在 SSH 提示时交互输入。登录服务器后：

```bash
ssh -i ~/.ssh/as2w_workstation -o StrictHostKeyChecking=accept-new zoubu@192.168.10.61 whoami
sftp -i ~/.ssh/as2w_workstation zoubu@192.168.10.61
# 在 sftp> 中先尝试：ls /D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO
# 核对路径后 exit，再挂载：
mkdir -p ~/as2w_workstation
sshfs -o IdentityFile="$HOME/.ssh/as2w_workstation",reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 \
  'zoubu@192.168.10.61:/D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO' ~/as2w_workstation
mountpoint -q ~/as2w_workstation && ls ~/as2w_workstation/AGENTS.md
```

上述 `/D:/Projects/...` SFTP 路径、SSHFS 挂载点与 `AGENTS.md` 读取均已实测。若 WiFi 改了工作站 IP，先用 Windows `Get-NetIPAddress -InterfaceAlias WLAN` 取新地址并替换命令。若挂载掉线，停止编辑，先 `fusermount3 -u ~/as2w_workstation` 再重新挂载；不要在空挂载目录继续写。

## 启动 OpenCode 和回写日志

挂载确认后在服务器执行：

```bash
cd ~/as2w_workstation
mkdir -p 部署测试/04_调试记录/logs
script -q -f "部署测试/04_调试记录/logs/$(date +%Y%m%d-%H%M%S)_opencode_tty.log" -c 'opencode .'
```

首次会话把 [给 OpenCode 的首条提示词](给OpenCode的首条提示词.md) 全文粘贴进去。该 `script` 终端记录直接写在工作站目录；OpenCode 自身的运行时缓存可能仍在服务器，结束时可再用 `opencode export <sessionID>` 导出会话 JSON 到工作站 `logs/`。提示词及项目日志不得包含密码、令牌或设备序列号。

从服务器让工作站执行已验证的**只读**阶段入口，示例：

```bash
ssh -i ~/.ssh/as2w_workstation zoubu@192.168.10.61 \
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/zoubu/as2w_field.ps1 -Stage GetState
```

该命令已从服务器实测成功：工作站调用 HDC，访问 USB 连接的 CPRO，返回 `fsm_name=ai_damping`，原始日志落在工作站 `部署测试/04_调试记录/logs/20261109-104554_windows_GetState.log`。它没有发布 LowCmd 或原厂高层动作的选项。服务器不能直接运行 Windows `hdc.exe`，也不直接连接机器人。若只想看文件/改代码，在 SSHFS 工作目录操作即可。源码改动后执行该入口的 `-Stage Sync`，再按需 `-Stage SdkBuild`。服务器终端可能把中文日志路径显示为乱码，但实际本地日志文件名与内容正常。

## Codex 交接（2026-11-09 12:30）

下午实机线交接给 Windows 工作站上的 Codex。首条提示词：[给Codex的交接提示词.md](给Codex的交接提示词.md)。
当前状态见 `../04_调试记录/INDEX.md` 10:46–12:30 各节；R41 以 `部署参考/cpp_deploy-as2w/models/r41/` 为准（ONNX Runtime 必须 1.22.0）。输入设备只用原厂遥控器。

## R152 续作（2026-11-09 15:12，覆盖上文旧 R41 主线）

用户指定 `omni-blind-stairs-r152` 为新部署目标；G1 16 轴人工状态映射已完成，服务器 MuJoCo R152 ONNX 固定集跟踪 44/52、严格接触 21/52，独立集 25/52、严格 9/52。完整实测、原始日志及限制见 `../04_调试记录/INDEX.md` 最新节；服务器下一条任务书是 [给OpenCode_R152续作提示词.md](给OpenCode_R152续作提示词.md)。

工作站→服务器另配置了专用免密 ed25519 密钥（私钥只在 `C:\Users\zoubu\.ssh\as2w_server`，不在项目）。从工作站可运行：

```powershell
ssh -i 'C:\Users\zoubu\.ssh\as2w_server' caolin@192.168.10.163
```

在服务器上先检查 `mountpoint -q ~/as2w_workstation`，再从挂载项目启动 OpenCode，并让它读取 `部署测试/05_OpenCode交接/给OpenCode_R152续作提示词.md`。项目源码与调试日志仍写工作站，服务器本地只放仿真依赖与计算缓存。**不重复做 G1 手动标定；R152 还没有实机闭环资格。**
