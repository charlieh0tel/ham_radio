#!/usr/bin/python3

import pickle
import sys

import matplotlib.pyplot as plt
import numpy as np


def main(argv):
    with open("thru_calibration.pkl", "rb") as f:
        cal = pickle.load(f)

    for k, trace in cal.items():
        frequencies = np.array(trace.frequencies) / 1e6
        amplitudes = np.array(list(trace.to_parameter_units()))
        mean = np.mean(amplitudes)
        std = np.std(amplitudes)
        
        print(f"  mean={mean:.3f} sd={std:.3f} {trace.amplitude_units} ")

        plt.plot(frequencies, amplitudes)
        plt.ylim(-20., 0.)
        
        plt.show()


    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
        
