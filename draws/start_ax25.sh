#!/bin/sh

set -o errexit
set -o xtrace

modprobe mkiss || :;

KISSTNC="/tmp/kisstnc"

TTY="$(realpath "${KISSTNC}")"

echo "TTY=${TTY}"

killall -9 kissattach || :;
sleep 1

kissattach "${TTY}" packet0
kissparms -c 1 -p packet0

ifconfig ax0
