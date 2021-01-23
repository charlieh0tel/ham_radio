#!/bin/sh

set -o errexit
set -o xtrace

MAC_ADDR="34:81:f4:33:aa:02"
RFCOMM_PORT=0
AXPORT=packet0

modprobe mkiss || :;

ifconfig ax0 down 2>/dev/null || :;
killall -9 kissattach 2>/dev/null || :;
sleep 1
rfcomm release ${RFCOMM_PORT} 2>/dev/null || :;
sleep 1
rfcomm bind ${RFCOMM_PORT} "${MAC_ADDR}" 6
kissattach "/dev/rfcomm${RFCOMM_PORT}" "${AXPORT}"

# todo: when we have ip addrblock add ip address
# ip route add 44.0.0.0/8 dev ax0

ifconfig ax0
