#!/usr/bin/env bash
# Read-only inventory for the AS2-W Orin expansion module, if SSH access exists.
set -u

echo '=== system ==='
uname -a
cat /etc/os-release 2>/dev/null || true

echo '=== interfaces and routes ==='
ip -br link 2>/dev/null || true
ip -br addr 2>/dev/null || true
ip route 2>/dev/null || true
ip rule 2>/dev/null || true

echo '=== relevant services (read only) ==='
ps -eo pid,comm,args 2>/dev/null | grep -Ei 'unitree|sport|motion|cyclone|dds' | grep -v grep || true
ss -lun 2>/dev/null | grep -E ':(7400|74[0-9][0-9])\b' || true

echo '=== SDK paths ==='
for path in /opt/unitree_robotics /home/unitree /data; do
    if [[ -d "$path" ]]; then ls -ld "$path"; fi
done
