# 2026-11-09 19:20–19:53 服务器时钟：CPRO 管理链 WiFi 化（hdc tconn + hdcrelay），全程无狗动作

环境：OpenCode 服务器（eai-MS-7E17，Ubuntu 24.04，wifi-x 内 192.168.10.163）经 SSH（密钥 ~/.ssh/as2w_workstation）驱动 Windows 工作站（zoubu@192.168.10.61，wifi-x，SSID 信号 84%）上的 `部署测试/00_HDC工具/hdc_6.1.1.280/hdc.exe`（Ver 3.2.0d）。CPRO：鸿蒙宿主 aarch64，HDC shell root，wlan0 192.168.10.180/24（wifi-x），eth0 192.168.123.100/24（机器人有线链，全程未动）。本记录不含密码/密钥内容/设备序列号；hdcrelay 日志时间为 UTC（+8 即本地）。

## 动机

用户希望拔掉 Windows PC↔CPRO 的 USB 线，改用 wifi-x 局域网管理 CPRO。

## 第一步：连通性验证（USB 未动）

- `netsh wlan show interfaces`：工作站 SSID=wifi-x，5 GHz 802.11ax，IPv4 192.168.10.61。
- `hdc shell "ip addr"`：CPRO wlan0 已在 wifi-x 网段（192.168.10.180/24，valid_lft forever）；eth0 192.168.123.100/24；`ip rule` 有既有 priority 1000 规则。
- ping 三向（工作站↔CPRO、服务器↔CPRO）全部不通：两端系统均不回 ICMP（Windows 防火墙默认丢弃；鸿蒙不回 echo）。**ICMP 不通不代表断网。**
- TCP 实测：工作站 `Test-NetConnection 192.168.10.180 -Port 6666` TcpTestSucceeded=True；服务器 `/dev/tcp/192.168.10.180/6666` 连接成功。服务器对全网段 8710 扫描当时无结果（原因见下）。

## 第二步：开启 hdcd TCP 模式

- 事前 netstat：无 8710 监听；`hdc tconn 192.168.10.180:8710` [Fail]Connect failed；Ubuntu chroot 无 sshd（`which sshd` 空）。
- `hdc tmode port 8710` → "Set device run mode successful"。help 确认：`tmode usb` / `tmode port [port]` / `tmode port close`。
- hdcd 守护进程（非整机）于 19:30:51 重启；**uptime 证实整机未重启**（后验 up 3 days），eth0 的 IP 和 ip rule 全程未丢。
- 重启后设备参数：`persist.hdc.mode=tcp`、`persist.hdc.port=8710`、`persist.hdc.mode.usb=enable`、`persist.hdc.mode.tcp=enable`（USB/TCP 双通道并存）；netstat 显示 `0.0.0.0:8710 LISTEN 53372/hdcd`。
- 教训：tmode 后 hdcd 重启约耗时 5 分钟，期间 tconn 一直失败；轮询窗口要放宽到 ≥8 分钟再用"失败"下结论。

## 第三步：关键发现——hdcd TCP 监听只收 lo 接口连接

- 外部（工作站/服务器）TCP 连 192.168.10.180:8710：**超时**（非拒绝），多次重试均 rc=124。
- 设备端 iptables：INPUT policy ACCEPT、ohfw_INPUT 空、无 8710 相关规则；路由表 99/2013/main 均正确含 192.168.10.0/24 dev wlan0。排除防火墙和策略路由。
- 同一设备上其余 wlan0 监听端口（62110/33637/44179/38293）从服务器**全部可正常建立 TCP 连接**——客户端互通无障碍，问题只针对 hdcd。
- 决定性实验（Ubuntu chroot 内 bash /dev/tcp）：设备自连 `127.0.0.1:8710` OK、自连 `192.168.10.180:8710` OK（本机流量走 lo）。
- **结论：该固件 hdcd 的 TCP 监听只接受从 lo 接口进入的连接，外部接口 SYN 被静默丢弃。判定为厂商安全加固（防止远程 root shell），非可配置项（param dump 无相关开关）。**

## 第四步：hdcrelay 中继

- 设计：微型 fork 型 TCP 中继，监听 `192.168.10.180:10178` → 转发 `127.0.0.1:8710`；自 daemon 化（fork+setsid+chdir+std 重定向），日志 `/data/local/tmp/as2w_field/hdcrelay.log`，TCP_NODELAY，半关闭正确传播。
- 源码：`部署参考/cpp_deploy-as2w/tools/hdcrelay.c`（随下次 准备现场包.ps1 入包）。
- 部署：`hdc file send`（绝对路径）→ `/data/local/tmp/as2w_field/hdcrelay.c` → 拷入 rootfs `/root/` → chroot 内 `gcc -static -O2` 编译（仅 -Wunused-result 警告，781088 B）→ 拷回 `/data/local/tmp/as2w_field/hdcrelay`。
- 启动关键：必须 `unshare --uts --fork /data/local/tmp/as2w_field/hdcrelay 192.168.10.180 10178 127.0.0.1 8710`。宿主 UTS 视图报内核 1.12.0，静态 glibc 二进制直接运行报 `FATAL: kernel too old`（SIGABRT）；unshare --uts 后内核视图为 5.10.43 即可运行（与项目已记录的 chroot 问题同源）。
- 启动成功：`netstat -tln` 显示 `192.168.10.180:10178 LISTEN`；日志 `hdcrelay up: 192.168.10.180:10178 -> 127.0.0.1:8710`。

## 第五步：验收（逐步切换到纯 WiFi）

1. 工作站 `hdc tconn 192.168.10.180:10178` → **Connect OK**；`list targets` 同时显示 USB SN 与 `192.168.10.180:10178`（并存时命令需 `-t`）。
2. `-t` shell `echo WIFI_HDC_OK` ✅。
3. `-t file send` hdcrelay.c 5676 B ✅，与 USB 版 md5 一致（67a0195abc1dfb9b1eb26ab7d0ba8376）。
4. chroot 入口 `-t shell "/data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc ..."` → CHROOT_OK ✅。
5. **拔掉 USB 线后**：`list targets` 仅剩 `192.168.10.180:10178`；裸 `hdc shell`（无 -t）执行成功；`file recv` 274 B 到 Windows 并核对 ✅；eth0（192.168.123.100/24）与 priority 1000 ip rule 完好。

## 结论

- PC↔CPRO 管理链已可纯 WiFi 运行，hdc 命令层用法与 USB 完全一致（单目标时无需 -t）；USB 随时可插回（mode.usb=enable）作为回退。
- CPRO→AS2-W 机器人有线链不受影响，全程未动。

## 未决与注意事项

1. **hdcrelay 不随 CPRO 重启存活**：重启后需经 USB（或尚存的通道）重新执行启动命令。hdcd 的 8710 监听参数已 persist，重启后自动恢复。
2. **安全**：10178 中继 = 把无认证 root shell 暴露给 wifi-x 全网段（hdcrelay 绑定 192.168.10.180 不能挡同网段主机）。仅适合受信网络；不用时 `pkill hdcrelay`（hdc shell）即可关闭。
3. 双通道并存（USB+WiFi）时所有 hdc 命令必须加 `-t <key>`。
4. `现场入口.ps1` 与 field.sh 命令层无需修改（hdc 抽象了传输层）；未验证现场入口脚本在纯 WiFi 下的自动探测行为。
5. DHCP 场景下 CPRO wlan0 IP 可能变化（当前 192.168.10.180 租约 forever）；IP 变化后需更新 tconn 目标与 hdcrelay 启动参数。
6. 下次 `准备现场包.ps1` 需把 `tools/hdcrelay.c` 纳入；当前设备上的二进制由本次手动部署，与源码一致。
