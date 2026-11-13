# OpenCode 服务器交接预检（2026-11-09）

- 工作站 WLAN：`192.168.10.61`；到服务器 `192.168.10.163` 的 TCP/22 测试通过。Ping 探测未成功，SSH 实际连接已成功，因此不用 ICMP 失败推断 SSH 不通。
- 已以 `caolin` SSH 登录服务器；系统 Ubuntu 24.04.4 x86_64，`opencode --version` 为 1.18.18；`opencode models` 能列出模型。服务器端安装了 `sshfs 3.7.3`（`sudo apt-get install -y sshfs`，仅新增该包，未升级现有包）。
- 服务器生成专用 ed25519 私钥 `~/.ssh/as2w_workstation`，私钥未复制到工作站或日志；对应公钥保存在 `部署测试/05_OpenCode交接/server_workstation.pub`，SHA256 指纹 `MUoO45OE6514fhoHehRS68QxIOlBgaXBXy46SRrH7do`。
- 工作站仅有 OpenSSH 客户端 `ssh.exe/scp.exe`；`sshd.exe` 不存在，端口 22 无监听。安装 OpenSSH Server 的系统命令需要管理员权限，当前代理进程为非提升管理员令牌，已准备 `部署测试/05_OpenCode交接/启用工作站SSH.ps1` 供现场用户在管理员 PowerShell 执行，尚未运行。
- 公钥指纹本地 `ssh-keygen -lf` 与服务器一致；交接目录未包含服务器登录密码。工作站 SSH 开通、服务器反向登录、SSHFS 挂载和从服务器远程调用 HDC 均待下一阶段实测，不标记为已通。
