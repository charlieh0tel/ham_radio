#!/usr/bin/python3

import json
import pathlib
import sys

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def main(argv):
    path = argv[1]

    for path in argv[1:]:
        with open(path, "r") as f:
            df = pd.read_csv(path)
        
            #df['amplitudes'] = df['amplitudes'].abs()
            df['frequencies'] = df['frequencies'] / 1e6

            ax = df.plot(x='frequencies', y='amplitudes')
            ax.minorticks_on()
            ax.set_ybound(0., -20.)

            gif_path = pathlib.Path(path).with_suffix(".png")
            plt.savefig(gif_path, dpi=300)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
