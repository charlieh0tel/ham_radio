#!/bin/sh

MAC_ADDR="34:81:f4:33:aa:02"

rfcomm bind 0 "${MAC_ADDR}" 6
