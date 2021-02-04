#!/bin/sh

set -o errexit
set -o xtrace

AXPORTNUM=0
AXPORT="packet${AXPORTNUM}"
IFPORT="ax${AXPORTNUM}"
TTY=/tmp/kisstnc

modprobe mkiss crc_force=1 || :;
ip link set dev "${IFPORT}" down 2>/dev/null || :;
kissattach "$(realpath "${TTY}")" "${AXPORT}"
kissparms -c 1 -p "${AXPORT}"

ip addr add dev "${IFPORT}" 44.4.9.21/30

ip link show dev "${IFPORT}"
