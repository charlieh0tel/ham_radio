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


def load_thru_calibrations():
    with open("thru_calibration.pkl", "rb") as f:
        return pickle.load(f)


def main(argv):
    #logging.basicConfig(level=logging.DEBUG)
    resource = "tcpip::e5810a::gpib0,11"
    adapter = pymeasure.adapters.VISAAdapter(resource, visa_library="@py",
                                             timeout=20 * 1000)
    sa = hp8560e.HP8560E(adapter)

    band_name = argv[1]
    band = bands.BAND_BY_NAME[band_name]
    thru_calibrations = load_thru_calibrations()
    
    print(f"{band_name} {band.start_frequency:.3f}  {band.stop_frequency:.3f}")
    calibration = thru_calibrations[band_name]
    #print(calibration)

    sa.preset()
    sa.start_frequency = band.start_frequency
    sa.stop_frequency = band.stop_frequency
    sa.write_trace(calibration, which='B')
    sa.normalize = True
    sa.sweep_coupling = "SR"
    sa.source_power = True
    sa.take_sweep()
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
