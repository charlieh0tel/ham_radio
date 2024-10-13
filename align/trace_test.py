#!/usr/bin/env python3

import pickle
import sys
import time

import numpy as np

import pymeasure
import pymeasure.adapters

import hp8560e
import noisy
import ablock

def escape_for_prologix(block):
    SPECIAL_CHARS = b'\x0d\x0a\x1b\x2b'
    new_block = b''
    for b in block:
        escape = b''
        if b in SPECIAL_CHARS:
            escape = b'\x1b'
            new_block += (escape + bytes((b,)))

    return new_block
    

def main(argv):
    serial = argv[1]
    id = int(argv[2])

    #adapter = pymeasure.adapters.PrologixAdapter(serial, 11)
    adapter = noisy.NoisyPrologixAdapter(serial, 11)

    sa = hp8560e.HP8560E(adapter)

    sa.preset()
    sa.start_frequency = 1e6
    sa.stop_frequency = 10e6
    sa.set_single_sweep_mode()
    #sa.take_sweep()

    r = [300] * sa.N_POINTS
    raw_bytes = ablock.to_ablock_u16(r)
    escaped_bytes = escape_for_prologix(raw_bytes)

    sa.write("TDF A;")
    sa.write_bytes(b"TRA " + raw_bytes)

    #print(f"r={r}")
    #sa.trace_a = r

    trace_a = sa.trace_a
    print(f"trace_a={trace_a}")

    """

    sa.trace_b = trace_a
    sa.write("VIEW TRB;")

    r = np.linspace(-80, 40, sa.N_POINTS, dtype=np.float64)
    r = [-20.] * sa.N_POINTS
    print(f"r={r}")
    sa.trace_a = r
    sa.trace_b = r
    
    sa.write("VIEW TRA;")
    time.sleep(2)
    sa.write("VIEW TRB;")

    """
    time.sleep(5)
    adapter.write("++loc")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
