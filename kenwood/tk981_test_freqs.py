#!/usr/bin/python3

import sys

_TEST_FREQ_START_OFFSET=0x172
_MEM_OFFSET=0x330


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def read_freq(dat, offset):
    s = (f"{dat[offset+3]:02x}{dat[offset+2]:02x}"
         f"{dat[offset+1]:02x}{dat[offset]:02x}")
    try:
        return float(s[0:3] + '.' + s[3:])
    except:
        return 0.0

         
def dump_mem_freqs(dat):
    print("memory freqs")
    offset = _MEM_OFFSET
    for i in range(500):
        rx = read_freq(dat, offset + 35)
        tx = read_freq(dat, offset + 39)
        if rx == 0: continue
        print(f"{i:2d} {rx:.4f} {tx:.4f}")
        offset += 64


def main(argv):
    path = argv[1]
    dat = read_bytes(path)

    print("test freqs")
    offset = _TEST_FREQ_START_OFFSET
    for i in range(10):
        rx = read_freq(dat, offset)
        tx = read_freq(dat, offset + 4)
        print(f"{i:2d} {rx:.4f} {tx:.4f}")
        offset += 2 * 4 + 2

    return 0

        


if __name__ == "__main__":
    sys.exit(main(sys.argv))
    
