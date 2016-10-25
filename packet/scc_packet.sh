#!/bin/bash

set -o errexit
set -o xtrace

DIREWOLF=$HOME/src/direwolf-1.2

${DIREWOLF}/direwolf -t 0 -c ${DIREWOLF}/direwolf.conf -p -d k  \
  >> direwolf.log  2>&1 &

sleep 1

R="$(mkiss -x 1 /tmp/kisstnc)"
PTS=$(echo ${R} | awk '{print $(NF);}')

sudo kissattach "${PTS}" radio 

exit 0
