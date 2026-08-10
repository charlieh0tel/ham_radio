"""Dependence and agreement against conductor gauge.

Agreement is the question the page cares about: does the shipped table,
fitted entirely at #14, predict other gauges within its stated x1.40?
Dependence is the diagnostic behind it: if the refitted coefficients
barely move with gauge, agreement is explained rather than lucky.
"""

import itertools

import numpy as np

from coefficients import VF_A, build_table, fitted_groups, interpolate
from fit import fit_group, load, model_zin
from gauge_sweep import GAUGES, SOIL
from nec_model import C

SWEEP = "gauge_sweep.npz"


def load_gauge():
    d = np.load(SWEEP, allow_pickle=False)
    return d, d["resistance"] + 1j * d["reactance"]


def shipped_table():
    """The #14 table the page carries, and the index of its average soil."""
    d, z = load()
    soils = list(d["soil_names"])
    return build_table(fitted_groups(d, z), len(soils)), soils.index(SOIL)


if __name__ == "__main__":
    table, soil_index = shipped_table()
    d, z = load_gauge()
    gauges = list(d["gauge_names"])

    print("AGREEMENT: shipped #14 table against each gauge")
    print(f"{'gauge':>7} {'radius mm':>10} {'median':>8} {'90th':>8} {'worst':>8}")
    for gi, gauge in enumerate(gauges):
        factors = []
        for freq, height, ret in itertools.product(
            np.unique(d["freq_hz"]), np.unique(d["height_m"]), np.unique(d["return_m"])
        ):
            sel = (
                (d["gauge"] == gi)
                & (d["freq_hz"] == freq)
                & (d["height_m"] == height)
                & (d["return_m"] == ret)
            )
            wavelength_m = C / freq
            alpha_a, ka, alpha_r, vf_r, kr = interpolate(
                table, soil_index, height / wavelength_m
            )
            # Z0 inside model_zin uses the module default radius (#14), so the
            # only way gauge enters is through the radius passed here.
            model = model_zin(
                (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
                d["ratio"][sel] * wavelength_m,
                height + d["return_m"][sel],
                wavelength_m,
                radius_m=GAUGES[gauge],
            )
            err = np.log(np.abs(model)) - np.log(np.abs(z[sel]))
            factors.append(np.exp(np.sqrt(np.mean(err**2))))
        f = np.array(factors)
        print(
            f"{gauge:>7} {GAUGES[gauge] * 1e3:10.3f} x{np.median(f):7.2f} "
            f"x{np.percentile(f, 90):7.2f} x{f.max():7.2f}"
        )

    print("\nDEPENDENCE: coefficients refitted per gauge, median over groups")
    names = ("alpha_a", "vf_a", "ka", "alpha_r", "vf_r", "kr")
    print(f"{'gauge':>7} " + " ".join(f"{n:>9}" for n in names))
    for gi, gauge in enumerate(gauges):
        rows = []
        for freq, height in itertools.product(
            np.unique(d["freq_hz"]), np.unique(d["height_m"])
        ):
            sel = (
                (d["gauge"] == gi) & (d["freq_hz"] == freq) & (d["height_m"] == height)
            )
            wavelength_m = C / freq
            params, _, _ = fit_group(
                d["ratio"][sel] * wavelength_m,
                height + d["return_m"][sel],
                wavelength_m,
                z[sel],
                radius_m=GAUGES[gauge],
            )
            rows.append(params)
        med = np.median(np.array(rows), axis=0)
        print(f"{gauge:>7} " + " ".join(f"{v:9.4f}" for v in med))
