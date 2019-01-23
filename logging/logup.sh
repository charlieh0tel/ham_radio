#!/bin/sh

set -o errexit

PATH="${HOME}/bin:$PATH"

FLDIGI_LOG="${HOME}/.fldigi/logs/logbook.adif"
WSJTX_LOG="${HOME}/.local/share/WSJT-X/wsjtx_log.adi"

for log in "${FLDIGI_LOG}" "${WSJTX_LOG}"; do
    echo "$log"
    tqsl -a=compliant -q -d -x -u "${log}" || :;
done
