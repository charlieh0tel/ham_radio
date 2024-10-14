#!/usr/bin/env python3

import pickle
import sys

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

import bands


def main(argv):
    sns.set_theme()

    with open("thru_calibration.pkl", "rb") as f:
        cal = pickle.load(f)

    for k, trace in cal.items():
        band = bands.which_band(trace.frequencies[0])
        frequencies = np.array(trace.frequencies) / 1e6
        amplitudes = np.array(list(trace.to_parameter_units()))
        mean = np.mean(amplitudes)
        std = np.std(amplitudes)
        
        print(f"band={band.name:10s}  mean={mean:6.3f} sd={std:6.3f} {trace.amplitude_units} ")
        
        title = (f"{band.name} mean={mean:.2f} std={std:.2f} dB")

        fig, ax = plt.subplots()
        ax.plot(frequencies, amplitudes, label=None)
        ax.set(xlabel="MHz", ylabel="IL (dB)", title=title)
        ax.minorticks_on()
        ax.set_ybound(0., -20.)

        plt.tight_layout()
        plt.show()


    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
