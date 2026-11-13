# AS2-W × CPRO 现场 bring-up 手册（2026-11-10 重写版）

**当前状态快照（详见 `../04_调试记录/INDEX.md` 11-10 各节）：**
- 已通过真机：Passive 安全唤醒（多次）、A 起立+固定 PD 站立（三次）、Y 受控趴下（三次）、B 门槛+零速交接（两次）、策略中 A 回站（三次从深塌陷拉正）；全程无报警。
- **暂停项**：R214 平地行走（后腿后仰塌陷机制 B，修复=T2 混合托底，未实施前禁止推摇杆行走）、侧移/旋转（训练命令域缺失）。
- 管理链：WiFi HDC `192.168.10.180:8710`（直连，2026-11-11 20:41 重启后实测可用，无需 hdcrelay；旧 `10178` 中继仅回退，详见 `实机事实与命令.md`）；CPRO eth0 `192.168.123.100/24`→狗 `.161`；发布端/launcher 见 `R214实机遥控与策略递进验收.md`。

**现场角色与停机原则（不变）：** 一人操作 CPRO，一人观察机器人、持原厂遥控器并确认原厂阻尼/急停；开阔平地、周围无人员。任何姿态不稳、状态失联或控制来源不明确，停止新命令，用已验证手段停止并记录。`StopMove` 不等于失能；软件返回空输出也不等于电机刹车。**急停是锁存式：按下后必须物理解除再上电，否则重启不上电（11-09 实测教训）。**

## 当前真机试验标准流程（11-10 实战固化）

1. **只读复核**（每次开始前）：`现场入口.ps1 -Stage MotionMode`（若仍 ReleaseMode 则 `name=` 空，不必重复释放；若原厂已恢复则重新申请 ReleaseMode）+ `-Stage LowState -Seconds 2`（约 1kHz、`mode_machine=2`）+ `-Stage LowCaptureFast -Seconds 2`（16 轴 mode 与姿态确认）。
2. **申请当次许可**：向现场人员说明本次具体动作（A→B→…→Y 链）、预期风险（塌陷/下沉/轮动）、自动退出（X/超时/物理急停），等明确同意。
3. **启动发布端**（经 SSH→PowerShell→hdc：`bash tools/run_r214_stand_trial.sh` 或 zero_b/motion）：等 `Passive ready after N frames`（狗趴着不动）。
4. **再开监测**：`-Stage LowCaptureFast -Seconds 150` 与 `-Stage LowProtection -Seconds 150`（各一条 ssh 后台）。**监测输出块缓冲、结束才回写；判定完成看帧数/末帧时间戳，达标后 pkill 回收**（`../AGENTS.md` 规则）。
5. **通知现场按键**：A→（站稳）→B→（按试验类型）→Y；现场人员逐段反馈姿态/异响。
6. **结束**：发布端自动停发 RC0 → 保存发布端日志与监测到 `../04_调试记录/logs/` → **立即追加 INDEX**（无论成败）→ 若需恢复原厂：SelectMode("ai") 会从趴下直接起立（须单独许可）。

## 环境重建参考（CPRO 重置/换机后；以下步骤 11-09 已全部验证）

- 传包：`hdc file send <本机包绝对路径> /data/local/tmp/as2w_field/`（**本机源必须绝对路径**，相对路径会在远端创建目录树）；远端 `sha256sum -c SHA256SUMS.txt` 后解包到 `/root/as2w_deploy`。
- 进入 Ubuntu：`/data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc '...'`（unshare mount+UTS；直接 chroot 报 kernel too old）。
- 网络：宿主侧 `cpro_host_net.sh apply`（eth0 加 `192.168.123.100/24`+路由规则，不改默认路由）；恢复 hdcrelay 见 WiFi 链文档。
- SDK2：安装后必须重跑 `tools/fix_sdk2_links.sh`（修复 Windows 签出的 .so.0 占位文本）；构建 `field.sh build`（7 CTest）→ `sdk-build`；R214 三构建见验收文档。
- 复杂远程命令用 base64 编码脚本传 CPRO 执行（多层引号转义规则在 `../AGENTS.md`）。

**历史注记：** 本页 11-09 版的"阶段 0-8 从零建立"清单（请同事确认、[Empty] 设备、六模型 bench、16 轴合同采集、影子推理等）已全部完成，完整过程见 `../04_调试记录/INDEX.md` 11-08/11-09 各节；本版仅保留可复用的环境重建技术步骤。