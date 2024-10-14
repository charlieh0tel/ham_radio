#!/usr/bin/env python3

import logging
import sys
import time

import numpy as np

import pymeasure
import pymeasure.adapters
import pyvisa

import hp8560e
import ablock

def main(argv):
    #logging.basicConfig(level=logging.DEBUG)
    resource = "tcpip::e5810a::gpib0,11"
    adapter = pymeasure.adapters.VISAAdapter(resource, visa_library="@py")
    sa = hp8560e.HP8560E(adapter)

    sa.preset()
    sa.start_frequency = 1e6
    sa.stop_frequency = 10e6
    sa.set_single_sweep_mode()
    sa.take_sweep()

    trace = sa.read_trace(which='A')
    print(trace)
    print(list(trace.to_parameter_units()))

    trace2 = sa.Trace(
        amplitude_units='DBM', reference_level=0.0, log_scale=10,
        trace_mu = [100] * sa.N_POINTS)

    sa.write_trace(trace2, which='B')
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
