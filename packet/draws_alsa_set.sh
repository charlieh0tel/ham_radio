#!/bin/bash

set -o nounset
set -o errexit
set -o xtrace

#
# https://nw-digital-radio.groups.io/g/udrc/wiki/8992
#
# IN1_L = LEFT PIN 4 (RX 9600 BAUD)
# IN1_R = RIGHT PIN 4 (RX 9600 BAUD)
# IN2_L = LEFT PIN 5 (RX 1200 BAUD)
# IN2_R = RIGHT PIN 5 (RX 1200 BAUD)
#
# LOL = LEFT PIN 1 (TX)
# LOR = RIGHT PIN 1 (TX)
#
# IO12 out = LEFT PIN 3 (PTT)
# IO23 out = RIGHT PIN 3 (PTT)
#
# IO25 in = LEFT PIN 6 (SQL)
# IO27 in = RIGHT PIN 6 (SQL)

function sset() {
    local name="$1"
    local setting="$2"
    amixer -c udrc -- sset "${name}" "${setting}"
}

#
# Settings are TX-790 #1 9600 baud
#

sset 'PCM' '0.0dB,-63.5dB'
sset 'ADC Level' '0.0dB,-12dB'
sset 'LO Driver Gain' '7.0dB,-6.0dB'
sset 'IN1_L to Left Mixer Positive Resistor' '10 kOhm'
sset 'IN1_R to Right Mixer Positive Resistor' 'Off'
sset 'IN2_L to Left Mixer Positive Resistor' 'Off'
sset 'IN2_R to Right Mixer Positive Resistor' 'Off'
sset 'DAC Left Playback PowerTune' 'P3'
sset 'DAC Right Playback PowerTune' 'P1'
sset 'LO Playback Common Mode' 'Full Chip'

#
sset 'CM_L to Left Mixer Negative Resistor' '10 kOhm'
sset 'CM_R to Right Mixer Negative Resistor' 'Off'
sset 'IN1_L to Right Mixer Negative Resistor' 'Off'
sset 'IN1_R to Left Mixer Positive Resistor' 'Off'
sset 'IN2_L to Right Mixer Positive Resistor' 'Off'
sset 'IN2_R to Left Mixer Negative Resistor' 'Off'
sset 'IN3_L to Left Mixer Positive Resistor' 'Off'
sset 'IN3_L to Right Mixer Negative Resistor' 'Off'
sset 'IN3_R to Left Mixer Negative Resistor' 'Off'
sset 'IN3_R to Right Mixer Positive Resistor' 'Off'
#
sset 'Mic PGA' 'off'
sset 'PGA Level' 0
#
sset 'ADCFGA Left Mute' 'off'
sset 'ADCFGA Right Mute' 'off'
sset 'AGC Attack Time' 0
sset 'AGC Decay Time' 0
sset 'AGC Gain Hysteresis' 0
sset 'AGC Hysteresis' 0
sset 'AGC Max PGA' 0
sset 'AGC Noise Debounce' 0
sset 'AGC Noise Threshold' 0
sset 'AGC Signal Debounce' 0
sset 'AGC Target Level' 0
sset 'AGC Left' 'off'
sset 'AGC Right' 'off'
#
#sset 'Auto-mute' 0
#
sset 'HP DAC' 'off'
sset 'HP Driver Gain' 0
sset 'HPL Output Mixer IN1_L' 'off'
sset 'HPL Output Mixer L_DAC' 'off'
sset 'HPR Output Mixer IN1_R' 'off'
sset 'HPR Output Mixer R_DAC' 'off'
#
sset 'LO DAC' 'on'
sset 'LOL Output Mixer L_DAC' 'on'
sset 'LOR Output Mixer R_DAC' 'on'
