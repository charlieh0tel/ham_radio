#!/bin/bash

set -o nounset
set -o errexit
#set -o xtrace

function cset() {
    local name="$1"
    local setting="$2"
    amixer -c dra-70 cset "${name}" "${setting}"
}

sudo systemctl stop direwolf || :;

# DRA-70 for TM-V71A
#
# R12 pointing just short of N
# R14 at first tick past zero
#
cset numid=3,iface=MIXER,name='Mic Playback Switch' off
cset numid=4,iface=MIXER,name='Mic Playback Volume' 0
cset numid=5,iface=MIXER,name='Speaker Playback Switch' on
cset numid=6,iface=MIXER,name='Speaker Playback Volume' 34,34
cset numid=7,iface=MIXER,name='Mic Capture Switch' on
cset numid=8,iface=MIXER,name='Mic Capture Volume' 1
cset numid=9,iface=MIXER,name='Auto Gain Control' off

sudo systemctl restart direwolf
sudo journalctl -u direwolf -f
