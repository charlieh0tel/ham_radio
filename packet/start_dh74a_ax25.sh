#!/bin/sh

set -o errexit
set -o xtrace

MACADDR="80:6f:b0:70:32:0d"   # Radio A
AXPORTNUM=1
RFCOMMPORT=1
RFCOMMCHAN=2
AXPORT="packet${AXPORTNUM}"
IFPORT="ax${AXPORTNUM}"
TTY="/dev/rfcomm${RFCOMMPORT}"
#TTY="/dev/ttyACM0"

modprobe mkiss || :;
ifconfig "${IFPORT}" down 2>/dev/null || :;

if [ -e "${TTY}" ]; then
  rfcomm release "${RFCOMMPORT}"
  sleep 1
fi  
rfcomm bind "${RFCOMMPORT}" "${MACADDR}" ${RFCOMMCHAN}
sleep 1
kissattach "${TTY}" "${AXPORT}"

ifconfig "${IFPORT}"
