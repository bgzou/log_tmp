# R4000 实机转向/提速反馈包（2026-11-13）

给训练侧的现场证据包：rolling-4000-stage020-research（model_3999.pt）在真机上的
0.4 m/s 直行与 ±0.1 rad/s 转向原始日志与分析。**核心结论：直行（含训练域外的 0.4）
良好；转向是"瞬态可转、持续 3 秒后停转"，策略轮输出全程饱和且差动分量为零，且
持续转向伴随后腿渐进下沉（安全相关）。**

读这个顺序：
1. `report/R4000_0.4m与转向实机分析_20261113.md` — 完整分析（表格、时间演化、根因链、训练建议 T1–T5）
2. `report/turn_mechanism.png` — 持续转向轮差塌缩+后腿下沉图
3. `analysis/turn_analysis.py` / `turn_analysis.txt` — 全部分析数字的可复算脚本与输出
4. `replay/` — **6101 帧实机观测回放夹具**（debug_policy.csv 逐策略帧生成）+ C++ 回放输出 + `compare_r4000_replay.py`（你们 compare_actor_replay.py 的 R4000 前缀版）——可直接对任意 checkpoint 回放
5. `data/` — 三次会话原始文件（debug_policy.csv=完整 65 维观测+raw/包装/目标 50 Hz、publisher/session/protection 日志、114335 会话的 2 ms 关键窗抽取）

会话清单：
- `20261113-114335_r4000`：120 s PolicyWalk，±0.4 m/s + 双向转向（主分析对象）
- `20261113-112630` / `112750`：±0.2 m/s 各 30 s（对照；直行质量与 114335 一致）

部署执行合同与训练运行 `filtered-4000-env4096-stage020.ovvRL3` 逐项一致
（5 Hz 腿滤波/0.9 rad/s 限速/pure_turn_common_scale=0/continuous+straight 站姿/
0.12 s 轮锁存），C++↔训练参考逐帧 parity 1.155e-07。

保护位三次会话全零、无软件守卫触发；0.2 rad/s 转向档在实测初态 MuJoCo 0/6
稳定（全翻+膝面 −1.2 cm），实机包络保持 0.1 rad/s——详见报告。

校验：`MANIFEST.sha256`。
