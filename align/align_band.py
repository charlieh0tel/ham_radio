#!/usr/bin/env python3

import datetime
import logging
import pickle
import sys
import time

import numpy as np

import pymeasure
import pymeasure.adapters

import bands
import hp8560e


def main(argv):
    #logging.basicConfig(level=logging.DEBUG)
    resource = "tcpip::e5810a::gpib0,11"
    adapter = pymeasure.adapters.VISAAdapter(resource, visa_library="@py",
                                             timeout=20 * 1000)
    sa = hp8560e.HP8560E(adapter)

    band_name = argv[1]
    band = bands.BAND_BY_NAME[band_name]
    print(f"{band_name} {band.start_frequency:.3f}  {band.stop_frequency:.3f}")

    sa.preset()
    sa.set_single_sweep_mode()
    sa.start_frequency = band.start_frequency
    sa.stop_frequency = band.stop_frequency
    sa.sweep_coupling = "SR"
    sa.source_power = True

    input("Attach thru.  Press return to continue. -> ")

    sa.write("SRCTKPK;")
    sa.wait_for_done()
    sa.take_sweep()
    sa.write("STORETHRU;")
    sa.take_sweep()
    sa.normalize = True

    sa.set_continuous_sweep_mode()
    print("Attach radio/filter and adjust if necessary.")
    input("Press return to continue to anaylize and record sweep. -> ")

    sa.set_single_sweep_mode()
    sa.take_sweep()
    trace = sa.read_trace()

    data = np.array(list(trace.to_parameter_units()))
    mean = np.mean(data)
    std = np.std(data)
    print(f"band={band_name} mean={mean:.3f} sd={std:.3f} dB")

    yymmdd = datetime.datetime.now().strftime("%y%m%d")
    with open(f"align_{band_name}_{yymmdd}.json", "w") as f:
        trace.to_dataframe().to_json(f)
    

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
