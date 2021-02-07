#!/bin/sh

GPIO=/usr/bin/gpio

if [ \! -x "${GPIO}" ]; then
    echo "$0: ${GPIO} missing from wiringpi package" 2>&1
    exit 1
fi

"${GPIO}" -g mode 12 out
"${GPIO}" -g mode 23 out
"${GPIO}" -g write 12 0
"${GPIO}" -g write 23 0


