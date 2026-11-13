#!/bin/bash
#
# Go2 v0.6.6 Xbox 手柄一键启动 (WiFi / 工作站模式 / UDP 连续控制)
#
# 架构:
#   Xbox 手柄 →USB-C→ 工作站 controller_sender.py →UDP/WiFi→ GO2 go2_ctrl --udp_input
#
# go2_ctrl 在 GO2 Orin 上运行 (DDS over eth0 到 MCU)。
# 工作站读取 Xbox 手柄 evdev 输入，将摇杆归一化为连续速度 {vx,vy,vyaw}，
# 以 50Hz UDP 发送到 GO2，go2_ctrl 通过 set_keyboard_velocity() 注入连续速度。
#
# 需要先部署:  bash cpp_stack/robogauge_code/go2_v066_wireless.sh deploy
# 需要重新编译 go2_ctrl (含 --udp_input 模式):
#   cd deploy/robots/go2 && cmake .. && make go2_ctrl
#
# 用法:
#   bash go2_v066_xbox_wifi_workstation.sh
#   bash go2_v066_xbox_wifi_workstation.sh --policy_dir <path-on-Go2>
#   POLICY_DIR=<path-on-Go2> bash go2_v066_xbox_wifi_workstation.sh
#
# SSH 认证: sshpass with Go2 default password. Override: GO2_PASS=xxx bash this_script.sh
#

set -euo pipefail

# ===== Configuration (keep in sync with go2_v066_wireless.sh) =====
GO2_USER="unitree"
GO2_WIFI_IP="192.168.31.126"     # Go2 wlan0 (WiFi SSH entry)
GO2_IFACE="eth0"                 # DDS interface ON the Go2 (MCU side)
GO2_DEPLOY_DIR="/home/unitree/robogauge_v066"
GO2_CTRL_BIN="${GO2_DEPLOY_DIR}/deploy/robots/go2/build/go2_ctrl"
GO2_SDK2_LIB="${GO2_DEPLOY_DIR}/sdk2_install/lib"
GO2_CPUINFO_FIX="${GO2_DEPLOY_DIR}/cpuinfo_jetson_fix.so"
LOCAL_WIFI_IFACE="enp5s0f0"      # local WiFi NIC
GO2_PASS="${GO2_PASS:-123}"
GO2_POLICY_DIR_DEFAULT="${GO2_DEPLOY_DIR}/logs/go2/go2_moe_cts_137k_0.6713"
UDP_PORT="4396"

# 本脚本所在目录 (用于找 controller_sender.py)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# controller_sender.py 所在目录 (go2_xbox_controller 仓库)
CONTROLLER_DIR="/home/robot/z00959834/go2_xbox_controller/scripts"

# ===== Parse args =====
POLICY_DIR="${POLICY_DIR:-$GO2_POLICY_DIR_DEFAULT}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --policy_dir)
            POLICY_DIR="$2"
            shift 2
            ;;
        --policy_dir=*)
            POLICY_DIR="${1#*=}"
            shift
            ;;
        --port)
            UDP_PORT="$2"
            shift 2
            ;;
        *)
            die "Unknown arg: $1"
            ;;
    esac
done

# ===== Helpers =====
log_info()  { echo "[INFO] $*"; }
log_pass()  { echo "[PASS] $*"; }
log_fail()  { echo "[FAIL] $*" >&2; }
log_step()  { echo; echo "========== Step $1: $2 =========="; }
die()       { log_fail "$*"; exit 1; }

ssh_go2() {
    sshpass -p "$GO2_PASS" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=5 \
        "${GO2_USER}@${GO2_WIFI_IP}" "$@"
}

ssh_go2_q() {
    sshpass -p "$GO2_PASS" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=5 \
        "${GO2_USER}@${GO2_WIFI_IP}" "$@"
}

# ===== Pre-flight =====
if [ ! -t 0 ]; then
    die "This script must be run in an interactive terminal."
fi

unset LD_LIBRARY_PATH LD_PRELOAD 2>/dev/null || true

# ================================================================
# Step 0: Xbox 手柄检查
# ================================================================
log_step 0 "Xbox 手柄检查"


if [ ! -f "${CONTROLLER_DIR}/controller_sender.py" ]; then
    die "controller_sender.py not found at ${CONTROLLER_DIR}/controller_sender.py"
fi
log_pass "0a: controller_sender.py found"

# 检查 evdev
if ! python3 -c "import evdev" 2>/dev/null; then
    die "python3-evdev not installed. Run: pip3 install evdev"
fi
log_pass "0b: python3-evdev available"

# 检查手柄是否连接
XBOX_DEVICE=$(python3 -c "
import evdev
for p in evdev.list_devices():
    try:
        d = evdev.InputDevice(p)
        if 'xbox' in d.name.lower() or 'microsoft' in d.name.lower():
            print(p)
            break
    except:
        pass
" 2>/dev/null)

if [ -z "$XBOX_DEVICE" ]; then
    die "Xbox 手柄未找到。请通过 USB-C 连接手柄并确认 /dev/input/ 下出现设备。"
fi
log_pass "0c: Xbox 手柄已连接 (${XBOX_DEVICE})"

# 检查 sshpass
if ! which sshpass >/dev/null 2>&1; then
    die "sshpass not installed. Run: sudo apt install sshpass"
fi
log_pass "0d: sshpass available"

# ================================================================
# Step 1: WiFi Link Check
# ================================================================
log_step 1 "WiFi Link Check"

if ! ip link show "$LOCAL_WIFI_IFACE" 2>/dev/null | grep -q 'state UP'; then
    die "Local WiFi interface $LOCAL_WIFI_IFACE is not UP."
fi
log_pass "1a: Local interface $LOCAL_WIFI_IFACE UP"

if ! ping -c 3 -i 0.2 -W 2 "$GO2_WIFI_IP" >/dev/null 2>&1; then
    die "Cannot reach $GO2_WIFI_IP over WiFi. Check robot power + WiFi."
fi
log_pass "1b: Go2 reachable ($GO2_WIFI_IP)"

if ! ssh_go2_q 'true' 2>/dev/null; then
    die "SSH to ${GO2_USER}@${GO2_WIFI_IP} failed. Check password (GO2_PASS env)."
fi
log_pass "1c: SSH OK"

# ================================================================
# Step 2: Deployment Validation
# ================================================================
log_step 2 "Deployment Validation"

if ! ssh_go2_q "[ -x ${GO2_CTRL_BIN} ] && echo YES || echo NO" 2>/dev/null | grep -q YES; then
    die "go2_ctrl not deployed on Go2 at ${GO2_CTRL_BIN}.
Run first: bash cpp_stack/robogauge_code/go2_v066_wireless.sh deploy"
fi
log_pass "2a: go2_ctrl deployed on Go2"

# 检查 go2_ctrl 是否支持 --udp_input
if ! ssh_go2_q "${GO2_CTRL_BIN} --help 2>&1" 2>/dev/null | grep -q "udp_input"; then
    die "go2_ctrl on Go2 does NOT support --udp_input.
Please rebuild and redeploy with the updated main.cpp:
  cd ${GO2_DEPLOY_DIR}/deploy/robots/go2 && cmake .. && make go2_ctrl"
fi
log_pass "2b: go2_ctrl supports --udp_input"

if ! ssh_go2_q "[ -d ${POLICY_DIR} ] && [ -f ${POLICY_DIR}/exported/policy.onnx ] && [ -f ${POLICY_DIR}/params/deploy.yaml ] && echo YES || echo NO" 2>/dev/null | grep -q YES; then
    die "Policy missing on Go2: ${POLICY_DIR}
Run: bash cpp_stack/robogauge_code/go2_v066_wireless.sh sync"
fi
log_pass "2c: Policy validated on Go2"

# ================================================================
# Step 3: Residual Process Check
# ================================================================
log_step 3 "Residual Process Check"

RESIDUAL="$(ssh_go2_q "pgrep -ax go2_ctrl || true" 2>/dev/null | grep -v Warning || true)"
if [ -n "$RESIDUAL" ]; then
    log_info "发现残留 go2_ctrl 进程，自动清理..."
    echo "$RESIDUAL"
    ssh_go2_q "pkill -INT -x go2_ctrl 2>/dev/null || true" 2>/dev/null
    sleep 2
    ssh_go2_q "pkill -x go2_ctrl 2>/dev/null || true" 2>/dev/null
    sleep 1
    RESIDUAL2="$(ssh_go2_q "pgrep -ax go2_ctrl || true" 2>/dev/null | grep -v Warning || true)"
    if [ -n "$RESIDUAL2" ]; then
        echo "$RESIDUAL2"
        die "无法清除残留 go2_ctrl 进程，请手动检查 GO2"
    fi
    log_pass "3: 残留进程已清除"
else
    log_pass "3: No residual go2_ctrl on Go2"
fi

# ================================================================
# Step 4: Launch (手柄 UDP → go2_ctrl --udp_input)
# ================================================================
log_step 4 "go2_ctrl Xbox 手柄模式 (UDP 连续控制)"

echo ""
echo "Robot is now reachable; control runs ON the Go2 Orin (DDS via eth0)."
echo "Xbox 手柄摇杆值以 50Hz UDP 连续发送到 GO2，实现丝滑连续控制。"
echo ""
echo "手柄按键映射 (UDP 连续控制模式):"
echo "  ┌─────────────┬──────────────────────────────────────────────┐"
echo "  │ Xbox 手柄    │ 功能                                          │"
echo "  ├─────────────┼──────────────────────────────────────────────┤"
echo "  │ A           │ FixStand (站立)                               │"
echo "  │ B           │ 启动 RL 策略 (Velocity_Up)                   │"
echo "  │ Y           │ Passive (软件停止, 趴下)                      │"
echo "  │ View        │ Passive (备用)                                │"
echo "  │ Xbox        │ 退出                                          │"
echo "  ├─────────────┼──────────────────────────────────────────────┤"
echo "  │ 左摇杆 Y    │ 前进/后退 (vx ±2.0 m/s, 连续比例控制)        │"
echo "  │ 左摇杆 X    │ 左移/右移 (vy ±1.0 m/s, 连续比例控制)        │"
echo "  │ 右摇杆 X    │ 左转/右转 (vyaw ±2.0 rad/s, 连续比例控制)    │"
echo "  │ 十字键      │ 同左摇杆 (叠加)                               │"
echo "  └─────────────┴──────────────────────────────────────────────┘"
echo ""
echo "连续控制说明:"
echo "  - 摇杆推到多少比例，速度就是多少比例 (与原生手柄一致)"
echo "  - 摇杆回中 → 速度自然归零"
echo "  - 低通滤波 + go2_ctrl 端 vx 阻尼 → 输出平滑"
echo "  - UDP 300ms 超时 → GO2 自动归零 (断连保护)"
echo "  - z 是软件 passive stop，不是物理急停"
echo ""
echo "  按 Xbox 中央按钮退出。"
echo ""

# 启动方式:
# 1. 在 GO2 上启动 go2_ctrl --udp_input (后台)
# 2. 在工作站上启动 controller_sender.py (前台)
# 3. controller_sender.py 退出后，SSH 到 GO2 停止 go2_ctrl

GO2_LAUNCH_CMD="cd ${GO2_DEPLOY_DIR}/deploy/robots/go2 && LD_LIBRARY_PATH=${GO2_SDK2_LIB}:\${LD_LIBRARY_PATH} LD_PRELOAD=${GO2_CPUINFO_FIX} ${GO2_CTRL_BIN} -n ${GO2_IFACE} -i 0 --udp_input --udp_port ${UDP_PORT} --policy_dir ${POLICY_DIR}"

log_info "在 GO2 上启动 go2_ctrl --udp_input (后台)..."
sshpass -p "$GO2_PASS" ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=5 \
    "${GO2_USER}@${GO2_WIFI_IP}" \
    "nohup bash -c '${GO2_LAUNCH_CMD}' > /tmp/go2_ctrl_udp.log 2>&1 &" 2>/dev/null
sleep 3

# 确认 go2_ctrl 已启动
if ! ssh_go2_q "pgrep -x go2_ctrl >/dev/null && echo YES || echo NO" 2>/dev/null | grep -q YES; then
    echo "--- GO2 log ---"
    ssh_go2_q "cat /tmp/go2_ctrl_udp.log 2>/dev/null || true" 2>/dev/null
    die "go2_ctrl failed to start on GO2. Check /tmp/go2_ctrl_udp.log on GO2."
fi
log_pass "go2_ctrl started on GO2 (UDP port ${UDP_PORT})"

log_info "启动手柄 UDP 发送器 (50Hz → ${GO2_WIFI_IP}:${UDP_PORT})..."
log_info "按 Ctrl+C 或 Xbox 按钮退出。"
echo ""

# 前台运行 controller_sender.py
# 退出后自动清理 GO2 上的 go2_ctrl
cleanup() {
    echo ""
    log_info "停止 GO2 上的 go2_ctrl..."
    ssh_go2_q "pkill -INT -x go2_ctrl 2>/dev/null || true" 2>/dev/null
    sleep 1
    ssh_go2_q "pkill -x go2_ctrl 2>/dev/null || true" 2>/dev/null
    log_info "清理完成。"
}
trap cleanup EXIT

python3 -u "${CONTROLLER_DIR}/controller_sender.py" "${XBOX_DEVICE}" \
    --host "${GO2_WIFI_IP}" --port "${UDP_PORT}"
RC=$?

echo ""
if [ "$RC" -eq 0 ]; then
    log_pass "Xbox 手柄会话结束 (rc=0)"
else
    log_fail "controller_sender exited with rc=$RC"
fi

# 显示 GO2 日志最后几行
echo ""
echo "--- GO2 go2_ctrl 日志 (最后 20 行) ---"
ssh_go2_q "tail -20 /tmp/go2_ctrl_udp.log 2>/dev/null || true" 2>/dev/null

exit "$RC"
