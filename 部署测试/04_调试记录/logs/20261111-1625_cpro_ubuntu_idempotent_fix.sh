#!/bin/sh
# Run one Ubuntu command from the CPRO HarmonyOS host, keeping mounts isolated.
# Idempotent since 2026-11-11: the HarmonyOS host already mounts /proc /sys /dev
# /dev/pts on the rootfs paths at boot (procfs/sysfs/devfs, hmmac=genfs), so
# re-mounting them raised "mount: Resource busy". Skip any path already listed
# in /proc/mounts before mounting the rest.
set -eu
rootfs=${AS2W_UBUNTU_ROOTFS:-/data/ubuntu_in_hm/ubuntu_rootfs}
if [ ! -x "$rootfs/bin/bash" ] || [ "$#" -lt 1 ]; then
    echo "Usage: AS2W_UBUNTU_ROOTFS=/path/to/rootfs $0 COMMAND [ARG...]" >&2
    exit 2
fi

exec unshare --mount --uts --fork /bin/sh -c '
    set -eu
    rootfs=$1
    shift
    grep -Fqs " $rootfs/proc " /proc/mounts    || mount -t proc proc "$rootfs/proc"
    grep -Fqs " $rootfs/sys " /proc/mounts     || mount -t sysfs sysfs "$rootfs/sys"
    mkdir -p "$rootfs/dev/pts" "$rootfs/dev/shm"
    grep -Fqs " $rootfs/dev " /proc/mounts     || mount -o bind /dev "$rootfs/dev"
    grep -Fqs " $rootfs/dev/pts " /proc/mounts || mount -o bind /dev/pts "$rootfs/dev/pts"
    grep -Fqs " $rootfs/dev/shm " /proc/mounts || mount -o bind /dev/shm "$rootfs/dev/shm"
    exec chroot "$rootfs" "$@"
' sh "$rootfs" "$@"