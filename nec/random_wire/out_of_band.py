"""What the tabulated model costs at frequencies it was never fitted on.

Everything coefficients.py reports is in-sample: the groups are fitted on
sweep.npz and the table is measured on sweep.npz.  An in-sample bound is
optimistic by construction, and it is the number that would otherwise
reach the page.

The sweep uses four frequencies -- 1.9, 7.15, 14.175 and 28.85 MHz -- so
the axis where extrapolation actually costs something is frequency: the
page evaluates nine bands and the fit has seen four.  This solves fresh
NEC cases at five frequencies in between and measures the tabulated model
against them.

That makes it the holdout.  A leave-one-group-out split would refit on
less data and degrade the coefficients that ship, for a number this
already answers in the axis that matters.
"""

import numpy as np

from coefficients import (
    MIN_H_OVER_LAMBDA,
    VF_A,
    build_table,
    fitted_groups,
    interpolate,
    refine_table,
)
from fit import load, model_zin
from nec_model import C, end_fed_zin

#: Band centres the sweep never saw, one per band it skipped.
UNSEEN_HZ = {
    "80m": 3.75e6,
    "30m": 10.125e6,
    "17m": 18.118e6,
    "15m": 21.225e6,
    "12m": 24.94e6,
}

#: Installations to test at each: the page's default and one either side.
SITES = (
    ("low", 3.0, 7.62),
    ("default", 9.144, 16.76),
    ("high", 25.0, 30.0),
)

RATIOS = np.arange(0.1, 2.6, 0.1)
SOIL = "average"


def measure(table, soil_index):
    """Tabulated error at each unseen frequency, over fresh NEC solves."""
    rows = []
    for band, freq_hz in UNSEEN_HZ.items():
        wavelength_m = C / freq_hz
        for name, height_m, return_m in SITES:
            if height_m / wavelength_m < MIN_H_OVER_LAMBDA:
                continue
            nec = np.array(
                [
                    end_fed_zin(
                        ratio * wavelength_m,
                        freq_hz,
                        height_m,
                        max(return_m - height_m, 1.0),
                        ground=SOIL,
                    )
                    for ratio in RATIOS
                ]
            )
            alpha_a, ka, alpha_r, vf_r, kr = interpolate(
                table, soil_index, height_m / wavelength_m
            )
            model = model_zin(
                (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
                RATIOS * wavelength_m,
                np.full(RATIOS.shape, return_m),
                wavelength_m,
            )
            err = np.log(np.abs(model)) - np.log(np.abs(nec))
            rows.append((band, name, float(np.exp(np.sqrt(np.mean(err**2))))))
    return rows


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])
    table = refine_table(build_table(fitted_groups(d, z), len(soils)), d, z, soils)
    rows = measure(table, soils.index(SOIL))

    print(f"{len(rows)} cases at {len(UNSEEN_HZ)} frequencies the fit never saw")
    print(f"{'band':>6} {'site':>9} {'error':>8}")
    for band, site, factor in rows:
        print(f"{band:>6} {site:>9} x{factor:7.2f}")

    factors = np.array([r[2] for r in rows])
    print(
        f"\nout of band: median x{np.median(factors):.2f}  "
        f"90th x{np.percentile(factors, 90):.2f}  worst x{factors.max():.2f}"
    )
    print(
        "compare the in-sample figures coefficients.py prints; the page "
        "should quote this one."
    )
