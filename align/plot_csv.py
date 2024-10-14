#!/usr/bin/env python3

import math
import json
import pathlib
import sys

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns

import bands


def main(argv):
    sns.set_theme()
    
    for path in argv[1:]:
        print(path)
        with open(path, "r") as f:
            df = pd.read_csv(path)
            band = bands.which_band(df['frequencies'][0])
            df['frequencies'] = df['frequencies'] / 1e6

            title = (f"{band.name} mean={df['amplitudes'].mean():.2f}, "
                     f"std={df['amplitudes'].std():.2f} dB")
            ax = df.plot(x='frequencies', y='amplitudes',
                         label=None)
            ax.get_legend().remove()
            ax.set(xlabel="MHz", ylabel="IL (dB)", title=title)
            ax.minorticks_on()
            y_max = 0 if df['amplitudes'].max() < 0. else 5.0
            y_min = min(math.ceil(df['amplitudes'].min() / -10.) * -10., -10.)
            ax.set_ybound(y_max, y_min)

            plt.tight_layout()
            
            gif_path = pathlib.Path(path).with_suffix(".png")
            plt.savefig(gif_path, dpi=300)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
