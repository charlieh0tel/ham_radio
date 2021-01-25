#!/bin/sh

set -o errexit
set -o xtrace

MACADDR="34:81:f4:33:aa:02"
AXPORTNUM=0
RFCOMMPORT=0
RFCOMMCHAN=6

AXPORT="packet${AXPORTNUM}"
IFPORT="ax${AXPORTNUM}"
TTY="/dev/rfcomm${RFCOMMPORT}"

modprobe mkiss || :;
ifconfig "${IFPORT}" down 2>/dev/null || :;
#killall -9 kissattach 2>/dev/null || :;
#sleep 1
if [ -e "${TTY}" ]; then
  rfcomm release "${RFCOMMPORT}"
  sleep 1
fi  
rfcomm bind "${RFCOMMPORT}" "${MACADDR}" ${RFCOMMCHAN}
sleep 1
kissattach "${TTY}" "${AXPORT}"

# todo: when we have ip addrblock add ip address
# ip route add 44.0.0.0/8 dev "${IFPORT}"

ifconfig "${IFPORT}"