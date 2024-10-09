#!/bin/bash

if [ $EUID -ne 0 ]; then
    echo "$0: need to run as root" 2>&1
    exit 1
fi

systemctl stop direwolf.service 
