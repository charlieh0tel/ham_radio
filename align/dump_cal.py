#!/usr/bin/python3

import pickle
import sys

import matplotlib.pyplot as plt
import numpy as np


def main(argv):
    with open("thru_calibration.pkl", "rb") as f:
        cal = pickle.load(f)

    for k, trace in cal.items():
        data = np.array(list(trace.to_parameter_units()))
        mean = np.mean(data)
        std = np.std(data)
        
        print(f"  mean={mean:.3f} sd={std:.3f} {trace.amplitude_units} ")

        """
        plt.plot(trace.frequencies, data + 100.)
        plt.yscale("log")
        plt.show()
        """


    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
        
