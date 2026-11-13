# CPRO 数据同步与远程操作（具体步骤）

适用：从 caolin 服务器向 CPRO 传文件/执行命令/回收日志的全部场景。本文是实测固化的 cookbook——每条都走过多次真链路。项目规则层面见 `AGENTS.md`，本文是操作手册。

## 1. 链路拓扑与前提

```
caolin 服务器 ──SSH──→ Windows 工作站 ──HDC──→ CPRO ──eth0──→ 机器狗
192.168.10.163        192.168.10.61 (zoubu)   192.168.10.180:8710
```

- caolin **不能直接碰 CPRO**（无 HDC、无直达网络）；一切经工作站中转。
- 工作站 SSH 免密已配：`ssh -i ~/.ssh/as2w_workstation zoubu@192.168.10.61`。
- HDC 客户端固定路径（不在 PATH）：`D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\00_HDC工具\hdc_6.1.1.280\hdc.exe`。
- CPRO 侧目录：源码 `/root/as2w_deploy`（宿主路径 `/data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy`）、助手 `/data/local/tmp/as2w_field/`、会话日志 `/root/field_sessions/`、ORT `/root/ort122`、SDK2 `/root/unitree_sdk2_install`。

## 2. 连通性检查与恢复（每次开工先做，只读）

```bash
# 工作站上看 HDC 目标状态（正常应 192.168.10.180:8710 TCP Connected）
ssh -i ~/.ssh/as2w_workstation zoubu@192.168.10.61 \
  "powershell.exe -NoProfile -Command \"& '<hdc.exe路径>' list targets -v\""
```
- 掉线（Offline）→ 重连一次即可：`... hdc.exe tconn 192.168.10.180:8710`。
- **禁令**：`hdc kill`（丢所有 tconn）、`hdc tmode`（重启 hdcd 约5分钟且可能切掉唯一通道）。
- 旧中继 `192.168.10.180:10178` 已弃用，仅极端回退。

## 3. 文件上传（工作站 → CPO）——两跳法

**第一跳 scp（必走英文路径 `C:\Users\zoubu\`，中文路径在命令行会炸）**：
```bash
scp -i ~/.ssh/as2w_workstation <本地文件> "zoubu@192.168.10.61:C:/Users/zoubu/rn_1.bin"
```
**第二跳 hdc file send（目标用 CPRO 宿主路径）**：
```bash
ssh ... "powershell.exe -NoProfile -Command \"& '<hdc.exe路径>' -t 192.168.10.180:8710 \
  file send 'C:\Users\zoubu\rn_1.bin' /data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy/<相对路径>\""
```

要点：
- **新目录要先建**（`file send` 不会自动建目录）：`hdc ... shell 'mkdir -p /data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy/<新目录>'`。
- **大文件禁用 base64 命令行传**（>~10KB 就会"参数列表过长"）；scp+file send 可传任意大小（实测 123KB 63ms、17MB 6s）。
- 多文件逐个传，或先在 caolin 打 tar 传一个再远端解包。
- **双端 SHA 核对**：传完在远端跑 `sha256sum` 与本地比对（用第 4 节的脚本法）。

## 4. 远程命令执行——base64 脚本法（四层链唯一可靠方式）

链路共四层 shell 解析（ssh → powershell → hdc shell → cpro_ubuntu.sh → bash），**禁止内联复杂命令**（变量 `$`、管道 `|`、`&&` 链会被中间层吃掉）。正确做法：

```bash
# 1) 把要在 CPRO Ubuntu 里执行的整段写成本地脚本
cat > /tmp/opencode/my_task.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd /root/as2w_deploy
# ... 具体命令 ...
EOF
# 2) base64 编码后单行传过去解码执行
B64=$(base64 -w0 /tmp/opencode/my_task.sh)
ssh -i ~/.ssh/as2w_workstation zoubu@192.168.10.61 \
  "powershell.exe -NoProfile -Command \"& '<hdc.exe路径>' -t 192.168.10.180:8710 shell \
  /data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc 'echo $B64 | base64 -d > /tmp/x.sh && bash /tmp/x.sh'\""
```
- `cpro_ubuntu.sh` 是进 Ubuntu rootfs 的入口（挂 proc/sys/dev 后 chroot）；**CPRO 宿主侧命令不要套它**（如 mkdir /data/... 直接裸 hdc shell）。
- 长输出会自动截断到文件，需要时用 grep/tail 取关键行。
- 远程删除源文件同法（先确认新文件可用再删旧的，见 05_重构范例）。

## 5. 整包同步 vs 定点同步（怎么选）

| 场景 | 方法 |
|---|---|
| 大范围源码改动/新策略接入 | **整包**：工作站 `-Stage Sync`（自动跑 `准备现场包.ps1` → tar → file send → 远端 sha256sum -c → 解包到 `/root/as2w_deploy`），一次到位 |
| 少数文件热修（1-10 个） | **定点**：第 3 节两跳法逐个传 + 双端 SHA，不动已验证旧 build 目录 |
| 需要远端重新编译 | 定点传完 → 第 4 节脚本法跑 `cmake --build build-rXXX --parallel $(nproc)` + `ctest` + audit |

## 6. ARM64 远端构建/测试（脚本模板）

```bash
cat > /tmp/opencode/cpro_build.sh <<'EOF'
#!/bin/bash
set -euo pipefail
cd /root/as2w_deploy
cmake --build build-rXXX --parallel "$(nproc)" 2>&1 | tail -4
ctest --test-dir build-rXXX --output-on-failure 2>&1 | tail -3
./build-rXXX/<binary路径> models/rXXX/deploy.yaml config/r152_measured.map --offline-audit 2>&1 | grep -aE "MAPPING PASS|AUDIT PASS"
sha256sum build-rXXX/<binary路径>
EOF
# 然后 base64 法执行；增量重编约几十秒，删 CMakeCache 才需要全量
```

## 7. 日志回收（CPRO → 工作站）

- **策略会话**：`运行现场策略会话.ps1` 自动完成——从输出抓 `dir=/root/field_sessions/...`，`file recv` 整目录回 `logs/field_sessions/`。无需手动。
- **手动取文件**：`hdc ... file recv /data/ubuntu_in_hm/ubuntu_rootfs/root/<路径> 'C:\Users\zoubu\'`，再 scp 回 caolin（反向两跳）。
- 会话四件套核大小：session.log / publisher.log / low_capture_fast.log / low_protection.log（+policy_diag.log）。

## 8. 常见坑（全部实际踩过）

| 坑 | 现象 | 解法 |
|---|---|---|
| 中文路径进命令行 | `-File 'D:\...\准备现场包.ps1'` 报"不支持给定路径的格式" | 改 `-Command "& '<路径>'"` 形式，或建无中文路径包装（已建 `C:\Users\zoubu\as2w_session.ps1`） |
| base64 塞大文件 | "参数列表过长" / 传一半断 | 一律 scp + file send |
| 新目录直接 file send | 静默失败 | 先 mkdir -p |
| CPRO 重启后 | tconn 目标消失 | 重连即可（persist.hdc.mode=tcp 自启）；旧"重启必须插USB起中继"结论已作废 |
| 双通道并存 | 裸 hdc 报 need connect-key | 命令一律带 `-t 192.168.10.180:8710` |
| Ctrl+C 想停远端 | 不保证传到 CPRO 发布端 | 运动中用 X/物理急停；只读监测挂住就 pkill 会话（数据为准，不看进程退出） |
| 监测抢 CPU | LowState 看门狗误触发（实测发生过） | 两个监测进程 `nice -n 10`（会话脚本已内置） |
| 时序误判 | ssh 链尾部挂住以为还在跑 | 以日志帧数/末帧时间戳为准，pkill 回收 |
