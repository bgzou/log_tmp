#!/bin/sh
# Run one Ubuntu command from the CPRO HarmonyOS host, keeping mounts isolated.
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
    # CPRO unshare -m isolates mounts; verified proc is absent outside.
    mount -t proc proc "$rootfs/proc"
    mount -t sysfs sysfs "$rootfs/sys"
    mkdir -p "$rootfs/dev/pts" "$rootfs/dev/shm"
    mount -o bind /dev "$rootfs/dev"
    mount -o bind /dev/pts "$rootfs/dev/pts"
    mount -o bind /dev/shm "$rootfs/dev/shm"
    exec chroot "$rootfs" "$@"
' sh "$rootfs" "$@"
