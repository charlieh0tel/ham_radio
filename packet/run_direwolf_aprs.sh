#!/bin/bash

HERE="$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")"

DIREWOLF=~/src/direwolf/build/src/direwolf
WHAT="$1"; shift
CONF="${HERE}/direwolf-${WHAT}-aprs.conf"

"${DIREWOLF}" -c "${CONF}" -d go -t 0 "$@" |& tee direwolf.log
