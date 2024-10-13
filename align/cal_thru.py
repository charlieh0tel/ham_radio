#!/usr/bin/env python3

import logging
import pickle
import sys
import time

import numpy as np

import pymeasure
import pymeasure.adapters

import bands
import hp8560e
import noisy


def main(argv):
    #logging.basicConfig(level=logging.DEBUG)
    resource = "tcpip::e5810a::gpib0,11"
    adapter = pymeasure.adapters.VISAAdapter(resource, visa_library="@py",
                                             timeout=20 * 1000)
    sa = hp8560e.HP8560E(adapter)
    
    print("Calibrating thru for all bands.")
    print("Setup thru calibration.")
    input("Press return to continue. -> ")

    band_thru_calibrations = dict()

    for band in bands.BANDS:
        print(f"Band {band.name}")

        sa.preset()
        sa.set_single_sweep_mode()
        sa.start_frequency = band.start_frequency
        sa.stop_frequency = band.stop_frequency
        sa.source_power = True
        sa.sweep_coupling = "SR"
        sa.write("SRCTKPK;")
        sa.wait_for_done()
        sa.take_sweep()
        sa.write("STORETHRU;")
        sa.take_sweep()
        sa.normalize = True

        band_thru_calibrations[band.name] = sa.read_trace(which='B')

        sa.write("VIEW TRB;")
        time.sleep(5)

    with open("thru_calibration.pkl", "wb") as f:
        pickle.dump(band_thru_calibrations, f)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
