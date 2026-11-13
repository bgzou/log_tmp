#!/bin/sh
# CPRO HarmonyOS host-side route for the robot subnet. No default route change.
set -eu

action=${1:-status}
nic=${AS2W_ROBOT_NIC:-eth0}
local_cidr=${AS2W_ROBOT_CIDR:-192.168.123.100/24}
robot_subnet=${AS2W_ROBOT_SUBNET:-192.168.123.0/24}
robot_ip=${AS2W_ROBOT_IP:-192.168.123.161}

if [ "$action" != status ] && [ "$action" != apply ]; then
    echo 'Usage: sh cpro_host_net.sh status|apply' >&2
    exit 2
fi

if [ "$action" = apply ]; then
    [ "$(id -u)" -eq 0 ] || { echo 'Root required' >&2; exit 1; }
    ip link show dev "$nic" >/dev/null
    ip link set "$nic" up
    if ! ip -4 addr show dev "$nic" | grep -Fq "inet $local_cidr"; then
        ip addr add "$local_cidr" dev "$nic"
    fi
    if ! ip rule show | grep -Eq "to $robot_subnet .*lookup main"; then
        ip rule add to "$robot_subnet" table main priority 1000
    fi
fi

ip -br addr show dev "$nic"
ip rule show
ip route get "$robot_ip"
ping -c 3 -W 1 -I "$nic" "$robot_ip"
