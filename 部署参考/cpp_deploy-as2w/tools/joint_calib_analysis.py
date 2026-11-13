#!/usr/bin/env python3
"""Offline AS2-W LOW_SAMPLE analysis. Never sends DDS or motor commands.

The report separates measured DDS slots from physical joint names. A person must
record the order and physical direction of each manual movement before filling
the mapping template; neither this script nor a URDF can establish that link.
"""

import argparse
import json
import math
import statistics
from pathlib import Path


MOTOR_COUNT = 35
ACTIVE_COUNT = 16
BASE_FIELDS = 13  # elapsed..gyro_z, excluding LOW_SAMPLE tag
EXPECTED_CELLS = 1 + BASE_FIELDS + 2 * MOTOR_COUNT


def load_samples(path):
    rows = []
    rejected = 0
    with path.open("r", encoding="utf-8-sig", errors="replace") as stream:
        for line in stream:
            if not line.startswith("LOW_SAMPLE,"):
                continue
            cells = line.rstrip("\r\n").split(",")
            if len(cells) != EXPECTED_CELLS:
                rejected += 1
                continue
            try:
                values = [float(cell) for cell in cells[1:]]
            except ValueError:
                rejected += 1
                continue
            if not all(math.isfinite(value) for value in values):
                rejected += 1
                continue
            if rows and values[0] <= rows[-1]["time_ms"]:
                rejected += 1
                continue
            rows.append({
                "time_ms": values[0],
                "age_ms": values[2],
                "gyro_z": values[12],
                "q": values[BASE_FIELDS::2],
                "dq": values[BASE_FIELDS + 1::2],
            })
    if not rows:
        raise ValueError(f"No complete, finite LOW_SAMPLE rows in {path}")
    return rows, rejected


def spans(flags, max_gap=0):
    """Return inclusive spans after bridging false runs of at most max_gap frames."""
    groups = []
    start = None
    last_true = None
    for index, flag in enumerate(flags):
        if flag:
            if start is None:
                start = index
            elif last_true is not None and index - last_true - 1 > max_gap:
                groups.append((start, last_true))
                start = index
            last_true = index
    if start is not None:
        groups.append((start, last_true))
    return groups


def median_q(rows, lo, hi, slot):
    return statistics.median(row["q"][slot] for row in rows[lo:hi])


def make_segments(rows, leg_threshold, wheel_threshold, gap_s, min_duration_s):
    flags = [
        any(abs(value) > leg_threshold for value in row["dq"][:12])
        or any(abs(value) > wheel_threshold for value in row["dq"][12:16])
        for row in rows
    ]
    # Use elapsed time rather than assumed sample rate; drop isolated spikes.
    raw = spans(flags)
    merged = []
    for start, end in raw:
        if merged and (rows[start]["time_ms"] - rows[merged[-1][1]]["time_ms"]) <= gap_s * 1000:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    results = []
    for start, end in merged:
        duration = (rows[end]["time_ms"] - rows[start]["time_ms"]) / 1000
        if duration < min_duration_s:
            continue
        # A short median window damps single-frame encoder noise at boundaries.
        edge = min(10, max(1, (end - start + 1) // 5))
        slot_data = []
        for slot in range(ACTIVE_COUNT):
            delta = median_q(rows, end - edge + 1, end + 1, slot) - median_q(rows, start, start + edge, slot)
            mean_dq = statistics.fmean(row["dq"][slot] for row in rows[start:end + 1])
            q_values = [row["q"][slot] for row in rows[start:end + 1]]
            slot_data.append({"slot": slot, "delta_q_rad": round(delta, 6), "direction": "+" if delta > 0 else "-" if delta < 0 else "0", "mean_dq_rad_s": round(mean_dq, 6), "q_range_rad": round(max(q_values) - min(q_values), 6)})
        ranked = sorted(slot_data, key=lambda item: abs(item["delta_q_rad"]), reverse=True)
        excursion_ranked = sorted(slot_data, key=lambda item: item["q_range_rad"], reverse=True)
        gyro_z = statistics.fmean(row["gyro_z"] for row in rows[start:end + 1])
        results.append({
            "number": len(results) + 1,
            "start_s": round(rows[start]["time_ms"] / 1000, 3),
            "end_s": round(rows[end]["time_ms"] / 1000, 3),
            "duration_s": round(duration, 3),
            "dominant_slot": ranked[0]["slot"],
            "second_slot": ranked[1]["slot"],
            "dominant_excursion_slot": excursion_ranked[0]["slot"],
            "mean_gyro_z_rad_s": round(gyro_z, 6),
            "slots": slot_data,
        })
    return results


def make_static(rows, leg_threshold, wheel_threshold, min_static_s):
    flags = [
        all(abs(value) <= leg_threshold for value in row["dq"][:12])
        and all(abs(value) <= wheel_threshold for value in row["dq"][12:MOTOR_COUNT])
        for row in rows
    ]
    windows = []
    for start, end in spans(flags, max_gap=2):
        duration = (rows[end]["time_ms"] - rows[start]["time_ms"]) / 1000
        if duration < min_static_s:
            continue
        subset = rows[start:end + 1]
        means = [statistics.fmean(row["q"][slot] for row in subset) for slot in range(ACTIVE_COUNT)]
        calf = statistics.fmean(means[slot] for slot in (2, 5, 8, 11))
        # Data-derived provisional posture label, not an operator confirmation.
        posture = "prone_candidate" if calf < -2.4 else "standing_candidate" if calf > -2.3 else "unknown"
        windows.append({
            "start_s": round(rows[start]["time_ms"] / 1000, 3),
            "end_s": round(rows[end]["time_ms"] / 1000, 3),
            "duration_s": round(duration, 3),
            "posture_candidate": posture,
            "q_mean_rad": [round(value, 6) for value in means],
        })
    anchors = {}
    for posture in ("prone_candidate", "standing_candidate"):
        candidates = [window for window in windows if window["posture_candidate"] == posture]
        if candidates:
            anchors[posture] = max(candidates, key=lambda window: window["duration_s"])
    return windows, anchors


def contract_names(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    in_names = False
    names = []
    for line in lines:
        if line == "joint_names:":
            in_names = True
            continue
        if in_names and line.startswith("- "):
            names.append(line[2:].strip())
        elif in_names:
            break
    if len(names) != ACTIVE_COUNT or len(set(names)) != ACTIVE_COUNT:
        raise ValueError(f"Expected {ACTIVE_COUNT} unique contract joint_names in {path}")
    return names


def turn_check(rows, segments):
    """Find yaw windows separately so lateral translation cannot dilute a turn."""
    turns = []
    raw = spans([abs(row["gyro_z"]) > 0.12 for row in rows])
    merged = []
    for start, end in raw:
        if merged and rows[start]["time_ms"] - rows[merged[-1][1]]["time_ms"] <= 300:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    for start, end in merged:
        if rows[end]["time_ms"] - rows[start]["time_ms"] < 500:
            continue
        subset = rows[start:end + 1]
        gyro = statistics.fmean(row["gyro_z"] for row in subset)
        if abs(gyro) * (rows[end]["time_ms"] - rows[start]["time_ms"]) / 1000 < 0.35:
            continue
        wheels = [statistics.fmean(row["dq"][slot] for row in subset) for slot in range(12, 16)]
        if abs(gyro) < 0.12 or max(abs(value) for value in wheels) < 0.6:
            continue
        right = statistics.fmean((wheels[0], wheels[2]))
        left = statistics.fmean((wheels[1], wheels[3]))
        if abs(right - left) < 0.6:
            continue
        consistent = (right - left) * gyro > 0
        midpoint = (rows[start]["time_ms"] + rows[end]["time_ms"]) / 2000
        parent = next((seg["number"] for seg in segments if seg["start_s"] <= midpoint <= seg["end_s"]), None)
        turns.append({"segment": parent, "start_s": round(rows[start]["time_ms"] / 1000, 3), "end_s": round(rows[end]["time_ms"] / 1000, 3), "yaw": "left" if gyro > 0 else "right", "gyro_z_rad_s": round(gyro, 4), "wheel_mean_dq_12_15": [round(value, 4) for value in wheels], "right_candidate_12_14": round(right, 4), "left_candidate_13_15": round(left, 4), "side_consistent": consistent})
    return turns


def render(report):
    out = ["# AS2-W 只读关节标定分析", "", f"源日志：`{report['input']}`", f"有效样本 {report['samples']}，丢弃行 {report['rejected_rows']}。候选姿态和轮侧别须结合现场动作记录复核。", "", "## 活动段", "", "段间空隙大于阈值才分段；主导槽按净 Δq 排名，轮滚动可能压过手掰腿轴。往返动作净位移会抵消，另列区间 q 范围最大槽。", "", "| 段 | 时间 s | 时长 s | 净 Δq 主导/次主导槽 | q 范围最大槽 | 平均 gyro_z rad/s |", "| --- | --- | ---: | --- | ---: | ---: |"]
    for seg in report["segments"]:
        out.append(f"| {seg['number']} | {seg['start_s']:.2f}–{seg['end_s']:.2f} | {seg['duration_s']:.2f} | {seg['dominant_slot']}/{seg['second_slot']} | {seg['dominant_excursion_slot']} | {seg['mean_gyro_z_rad_s']:.3f} |")
    out += ["", "### 每段 0–15 槽净位移 Δq / 平均 dq / q 范围", ""]
    for seg in report["segments"]:
        out.append(f"**段 {seg['number']}** ({seg['start_s']:.2f}–{seg['end_s']:.2f} s)：" + "; ".join(f"{slot['slot']}:Δ{slot['delta_q_rad']:+.3f} rad/dq{slot['mean_dq_rad_s']:+.3f} rad/s/range{slot['q_range_rad']:.3f} rad" for slot in seg["slots"]))
        out.append("")
    out += ["## 已知转向交叉检查", "", "按 gyro_z 左正右负、前进轮 dq 正的现场事实，检验 12/14 右、13/15 左；此项只校验旧采样，不能代替逐轮标定。", "", "| 段 | 时间 s | 方向 | gyro_z | dq12,13,14,15 | 侧别一致 |", "| --- | --- | --- | ---: | --- | --- |"]
    for turn in report["turn_checks"]:
        out.append(f"| {turn['segment']} | {turn['start_s']:.2f}–{turn['end_s']:.2f} | {turn['yaw']} | {turn['gyro_z_rad_s']:+.3f} | {', '.join(f'{v:+.2f}' for v in turn['wheel_mean_dq_12_15'])} | {turn['side_consistent']} |")
    out += ["", "## 趴下/站立静态读数", "", "选取每态最长的全 16 槽低速窗口；轮 q 是累计转角，不是姿态零位。", "", "| DDS 槽 | 趴下候选 q rad | 站立候选 q rad |", "| ---: | ---: | ---: |"]
    anchors = report["static_anchors"]
    for slot in range(ACTIVE_COUNT):
        prone = anchors.get("prone_candidate", {}).get("q_mean_rad", [])
        stand = anchors.get("standing_candidate", {}).get("q_mean_rad", [])
        out.append(f"| {slot} | {prone[slot]:.5f} | {stand[slot]:.5f} |" if prone and stand else f"| {slot} | {prone[slot]:.5f} | — |" if prone else f"| {slot} | — | {stand[slot]:.5f} |" if stand else f"| {slot} | — | — |")
    out += ["", "### 全部静态窗口", "", "| 时间 s | 时长 s | 姿态候选 |", "| --- | ---: | --- |"]
    for window in report["static_windows"]:
        out.append(f"| {window['start_s']:.2f}–{window['end_s']:.2f} | {window['duration_s']:.2f} | {window['posture_candidate']} |")
    out += ["", "## Contract 关节序 → DDS 槽位/符号（人工填写模板）", "", "只有现场记录的物理关节、手掰方向与对应活动段能填槽位和 sign；本表不自动赋值。offset 需另行站姿标定。", "", "| contract 序号 | joint_names | 动作段号 | DDS 槽位 | 物理正方向 | sign | 趴下 q | 站立 q | 证据 |", "| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |"]
    for entry in report["mapping_template"]:
        out.append(f"| {entry['contract_index']} | {entry['joint_name']} |  |  |  |  |  |  |  |")
    out += ["", "**禁止把未核实模板当 calibrated.map 使用；本工具不发送任何控制命令。**", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--contract", type=Path, default=Path(__file__).resolve().parents[1] / "models/r41/deploy.yaml")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[3] / "部署测试/04_调试记录/logs")
    parser.add_argument("--leg-dq", type=float, default=0.12, help="Activity threshold, rad/s")
    parser.add_argument("--wheel-dq", type=float, default=0.3, help="Wheel activity threshold, rad/s")
    parser.add_argument("--gap-s", type=float, default=1.5, help="Maximum gap merged into an activity segment")
    parser.add_argument("--min-segment-s", type=float, default=0.25)
    parser.add_argument("--min-static-s", type=float, default=1.0)
    parser.add_argument("--check-known-turns", action="store_true", help="Assert the 11:41 sample contains the known left/right wheel side pattern")
    args = parser.parse_args()
    for value in (args.leg_dq, args.wheel_dq, args.gap_s, args.min_segment_s, args.min_static_s):
        if value <= 0:
            parser.error("All thresholds and durations must be positive")
    rows, rejected = load_samples(args.log)
    segments = make_segments(rows, args.leg_dq, args.wheel_dq, args.gap_s, args.min_segment_s)
    static_windows, anchors = make_static(rows, args.leg_dq, args.wheel_dq, args.min_static_s)
    names = contract_names(args.contract)
    report = {
        "input": str(args.log.resolve()), "samples": len(rows), "rejected_rows": rejected,
        "thresholds": {"leg_dq_rad_s": args.leg_dq, "wheel_dq_rad_s": args.wheel_dq, "gap_s": args.gap_s, "min_segment_s": args.min_segment_s, "min_static_s": args.min_static_s},
        "segments": segments, "static_windows": static_windows, "static_anchors": anchors,
        "turn_checks": turn_check(rows, segments),
        "mapping_template": [{"contract_index": index, "joint_name": name, "activity_segment": None, "dds_slot": None, "physical_positive_direction": None, "sign": None, "prone_q_rad": None, "standing_q_rad": None, "evidence": None} for index, name in enumerate(names)],
    }
    if args.check_known_turns:
        left_ok = any(turn["yaw"] == "left" and turn["side_consistent"] and turn["wheel_mean_dq_12_15"][0] > 0 and turn["wheel_mean_dq_12_15"][1] < 0 and turn["wheel_mean_dq_12_15"][2] > 0 for turn in report["turn_checks"])
        right_ok = any(turn["yaw"] == "right" and turn["side_consistent"] and turn["wheel_mean_dq_12_15"][0] < 0 and turn["wheel_mean_dq_12_15"][1] > 0 and turn["wheel_mean_dq_12_15"][3] > 0 for turn in report["turn_checks"])
        if not (left_ok and right_ok):
            raise SystemExit("Known turn cross-check FAILED: expected 12/14 right, 13/15 left in opposite yaw directions")
        print("Known turn cross-check PASS: 12/14 right, 13/15 left in opposite yaw directions")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.log.stem + "_joint_calib_analysis"
    json_path = args.output_dir / (stem + ".json")
    markdown_path = args.output_dir / (stem + ".md")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render(report), encoding="utf-8")
    print(f"samples={len(rows)} rejected={rejected} segments={len(segments)} static_windows={len(static_windows)} turns={len(report['turn_checks'])}")
    print(f"json={json_path}\nmarkdown={markdown_path}")
    for turn in report["turn_checks"]:
        print(f"turn segment={turn['segment']} {turn['start_s']:.2f}-{turn['end_s']:.2f}s {turn['yaw']} wheels={turn['wheel_mean_dq_12_15']} side_consistent={turn['side_consistent']}")


if __name__ == "__main__":
    main()
