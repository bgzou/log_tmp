#!/usr/bin/env bash
set -euo pipefail
b2w_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
b2w_python="${AS2W_BASE_PYTHON:-${B2W_BASE_PYTHON:-/home/chenzihao/miniconda3/envs/roboparty/bin/python}}"
if [[ ! -x "$b2w_python" ]]; then
  echo "Set B2W_BASE_PYTHON to a Python with Isaac Sim 5.1, Isaac Lab 2.3.2 and CUDA PyTorch installed." >&2
  exit 1
fi
if [[ ! -x "$b2w_root/.venv/bin/python" ]]; then
  "$b2w_python" -m venv --system-site-packages "$b2w_root/.venv"
fi
uv pip install --python "$b2w_root/.venv/bin/python" --no-deps 'mujoco==3.2.7' 'rsl-rl-lib==3.3.0'
"$b2w_root/.venv/bin/python" "$b2w_root/scripts/bootstrap.py"
if command -v apt-get >/dev/null && command -v dpkg-deb >/dev/null && [[ ! -x "$b2w_root/tools/xvfb/root/usr/bin/Xvfb" ]]; then
  mkdir -p "$b2w_root/tools/xvfb/packages"
  (cd "$b2w_root/tools/xvfb/packages" && apt-get download xvfb xauth xserver-common)
  for b2w_package in "$b2w_root"/tools/xvfb/packages/*.deb; do
    dpkg-deb -x "$b2w_package" "$b2w_root/tools/xvfb/root"
  done
fi
"$b2w_root/.venv/bin/python" "$b2w_root/scripts/doctor.py" --verify-sources
