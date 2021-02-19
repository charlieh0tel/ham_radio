#!/bin/bash

set -o xtrace
set -o errexit

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

TMPCONF=$(mktemp)
trap "rm -f $TMPCONF" EXIT

if [ "x$1" == "x" ]; then
    echo "usage: $0 port" 1>&2
    exit 1
fi

perl -p -e "s@XXPORTXX@$1@g" < "${HERE}/aprx_rx_igate.conf" >"${TMPCONF}"

aprx -i -v -d -d -d -L -f "${TMPCONF}"
