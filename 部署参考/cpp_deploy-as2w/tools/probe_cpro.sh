#!/usr/bin/env bash
set -u

echo '=== runtime ==='
uname -a
uname -m
cat /etc/os-release 2>/dev/null || true
id
command -v g++ || true
command -v cmake || true

echo '=== networking (read only) ==='
ip -br link 2>/dev/null || true
ip -br addr 2>/dev/null || true
ip route 2>/dev/null || true
ip rule 2>/dev/null || true
if command -v ping >/dev/null 2>&1; then
    echo '=== robot PC1 connectivity ==='
    ping -c 3 -W 1 192.168.123.161 2>&1 || true
fi

echo '=== USB and input ==='
cat /proc/bus/input/devices 2>/dev/null || true
ls -l /dev/input 2>/dev/null || true
lsusb 2>/dev/null || true

echo '=== namespace and mounts ==='
readlink /proc/self/ns/net 2>/dev/null || true
readlink /proc/self/ns/mnt 2>/dev/null || true
mount | grep -E '(/dev |/dev/input|/proc |/sys )' || true

echo '=== SDK / model prerequisites ==='
test -f /opt/unitree_robotics/lib/libunitree_sdk2.a && echo 'SDK2 static library present in /opt' || true
test -f /opt/unitree_robotics/lib/cmake/unitree_sdk2/unitree_sdk2Config.cmake && echo 'SDK2 CMake package present in /opt' || true
