## 2026-11-13 17:05–17:10：网段再次变动（服务器 192.168.10.13 / 工作站 192.168.10.34），重新挂载 SSHFS（无狗动作）

- 现象：用户报告地址“变成 10.13”。只读探测：工作站 WLAN `192.168.10.34/24`；`Test-NetConnection` 显示 `192.168.10.13:22` 通，旧地址 `192.168.10.163:22`、`192.168.43.12:22` 均不通。服务器 hostname 仍为 `eai-MS-7E17`，与下午是同一台。
- 防火墙：`AS2W-OpenCode-Workstation-SSH` 原 `RemoteAddress=192.168.10.163,192.168.43.12`，不含 `.13`，故服务器→工作站 `ssh` 再次超时（与 15:36 同机制，非链路问题）。管理员权限改为 `192.168.10.163,192.168.43.12,192.168.10.13`，读回一致；原始日志 `logs/20261113_1707_workstation_ssh_firewall_fix_1013.log`。修复后 `zoubu@192.168.10.34 whoami` 返回 `bgzou9897\zoubu`。
- 挂载：下午的 sshfs 进程（PID 358436，指向 `192.168.43.4`）随网络切换失效，挂载点 stale（`mountpoint` 报“输入/输出错误”）。kill 旧进程 → `fusermount3 -u`（此时已无 mtab 条目，报 `not found` 属预期）→ 重挂 `sshfs -o IdentityFile=/home/caolin/.ssh/as2w_workstation,reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 'zoubu@192.168.10.34:/D:/Projects/Athena/运动控制/Collie/AS2-W_CPRO' /home/caolin/as2w_workstation`。验证：`mountpoint -q` 通过、`AGENTS.md` 可读、写入→读回→删除探针文件成功，且挂载点立即可见下午新增的 INDEX 节。
- 文档同步：`05_OpenCode交接/README.md` 顶部地址说明改为“当前 192.168.10.13 / 192.168.10.34，下午曾 192.168.43.12 / 192.168.43.4”；`启用工作站SSH.ps1` 默认 `RemoteAddress` 加入 `192.168.10.13`（重跑即更新规则，ParseFile 校验 PARSE OK）。
- 复用口诀（地址再变时照做）：① `Get-Service sshd` 与 `Test-NetConnection` 确认两边可达；② 管理员执行 `Set-NetFirewallRule -Name 'AS2W-OpenCode-Workstation-SSH' -RemoteAddress @(<新服务器IP>, 旧IP…)`；③ 服务器上 kill 旧 `sshfs` → `fusermount3 -u ~/as2w_workstation` → 以新 `zoubu@<工作站IP>:/D:/...` 重挂；④ 更新 README/INDEX。
- 未做：无 HDC、无 ReleaseMode、无 LowCmd、无狗动作；未改部署源码/模型/现场包。
