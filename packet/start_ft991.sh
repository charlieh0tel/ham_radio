#!/bin/bash

set -o errexit
set -o xtrace

HERE="$(pwd)"

DIREWOLF=$HOME/src/direwolf

${DIREWOLF}/direwolf -t 0 -c "${HERE}/direwolf-ft991.conf" -p -d k  \
  >> direwolf.log  2>&1 &

sleep 1

R="$(mkiss -x 1 /tmp/kisstnc)"
PTS=$(echo ${R} | awk '{print $(NF);}')

sudo kissattach "${PTS}" radio 

exit 0
