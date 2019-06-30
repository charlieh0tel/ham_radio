#!/bin/sh

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

aprx -v -d -L -f "${HERE}/aprx.conf"
