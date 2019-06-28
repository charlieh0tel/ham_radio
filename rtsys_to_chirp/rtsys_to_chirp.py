#!/usr/bin/python

import csv
import sys

_RTSYS_FIELD_NAMES = [
    'Channel Number',
    'Receive Frequency',
    'Transmit Frequency',
    'Offset Frequency',
    'Offset Direction',
    'Operating Mode',
    'Name',
    'Tone Mode',
    'CTCSS',
    'Rx CTCSS',
    'DCS',
    'DCS Polarity',
    'Lockout',
    'Step',
    'Group',
    'Comment',
    'Digital Squelch',
    'Digital Code',
    'Your Callsign',
    'Rpt-1 CallSign',
    'Rpt-2 CallSign',
    'Fine Step Enable',
    'Fine Step'
]

_CHIRP_FIELD_NAMES = [
    'Location',
    'Name',
    'Frequency',
    'Duplex',
    'Offset',
    'Tone',
    'rToneFreq',
    'cToneFreq',
    'DtcsCode',
    'DtcsPolarity',
    'Mode',
    'TStep',
    'Skip',
    'Comment',
    'URCALL',
    'RPT1CALL',
    'RPT2CALL',
    'DVCODE'
]

def _RtsysOffsetToMHz(offset):
    (mag_str, suffix) = offset.split(' ')
    mag = float(mag_str)
    if suffix == 'MHz':
        return mag
    elif suffix == 'kHz':
        return mag / 1000.
    else:
        assert "bad suffix"

def _RtsysOffsetDirectionToChirpDuplex(offset_direction):
    if offset_direction == 'Plus':
        return '+'
    elif offset_direction == 'Minus':
        return '-'
    elif offset_direction == 'Simplex':
        return ''
    else:
        assert "bad offset direction"

def _RtsysToneModeToChirpTone(tone_mode):
    if tone_mode == 'Tone':
        return 'Tone'
    elif tone_mode == 'T Sql':
        return 'TSQL'
    elif tone_mode == 'None':
        return ''
    else:
        assert "bad tone mode"
    
def _RtsysCTCSSToHz(ctcss):
    assert ctcss.endswith(" Hz")
    return ctcss[:-3]

def main(argv):
  with open(argv[1]) as rtsys:
    with open(argv[2], 'w') as chirp:
      rtsys_reader = csv.DictReader(rtsys, fieldnames=_RTSYS_FIELD_NAMES)
      chirp_writer = csv.DictWriter(chirp, fieldnames=_CHIRP_FIELD_NAMES)
      chirp_writer.writeheader()
      header = True
      for row in rtsys_reader:
        if header:
            header = False
            continue
        chirp_row = {
            'Location': row['Channel Number'],
            'Name': row['Name'],
            'Frequency': row['Receive Frequency'],
            'Duplex': _RtsysOffsetDirectionToChirpDuplex(row['Offset Direction']),
            'Offset': _RtsysOffsetToMHz(row['Offset Frequency']),
            'Tone': _RtsysToneModeToChirpTone(row['Tone Mode']),
            'rToneFreq': _RtsysCTCSSToHz(row['CTCSS']),
            'cToneFreq': _RtsysCTCSSToHz(row['Rx CTCSS']),
            'DtcsCode': '023',  # apparently something is needed
            'DtcsPolarity': 'NN', # ditto
            'Mode': row['Operating Mode'],
            'TStep': '5.00',    # ditto
            'Skip': '',
            'Comment': '',
            'URCALL': '',
            'RPT1CALL': '',
            'RPT2CALL': '',
            'DVCODE': '',
        }
        chirp_writer.writerow(chirp_row)

if __name__ == "__main__":
  main(sys.argv)
    
