#!/usr/bin/env python3

import pickle
import sys
import time

import numpy as np

import pymeasure
import pymeasure.adapters

import bands
import hp8560e
import noisy


def load_thru_calibrations():
    with open("thru_calibration.pkl", "rb") as f:
        return pickle.load(f)


def main(argv):
    serial = argv[1]
    id = int(argv[2])
    band_name = argv[3]
    band = bands.BAND_BY_NAME[band_name]
    thru_calibrations = load_thru_calibrations()
    
    #adapter = pymeasure.adapters.PrologixAdapter(serial, 11)
    adapter = noisy.NoisyPrologixAdapter(serial, 11)

    sa = hp8560e.HP8560E(adapter)
    
    sa.preset()
    sa.start_frequency = band.start_frequency
    sa.stop_frequency = band.stop_frequency
    sa.trace_b = thru_calibrations[band_name]

    #sa.write("RCLTHRU;")
    #sa.normalize = True
    #sa.sweep_coupling = "SR"
    #sa.source_power = True

    adapter.write("++loc")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
