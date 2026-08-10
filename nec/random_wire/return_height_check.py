"""Can the two-line model absorb the return path's height?

Two questions, as with gauge.

  agreement   does the shipped table, fitted at a 5 cm return, still
              predict other return heights within the stated bound?
  dependence  if not, do the return line's own alpha, velocity factor
              and Z0 scale move smoothly with it?

Dependence is the hopeful case: return height is a property of the return
line, and that line already carries three fitted parameters.  If they
absorb it smoothly it becomes another axis to tabulate against, and the
page can offer it as a control rather than an unmodelled caveat.
"""

import itertools

import numpy as np

from coefficients import VF_A, build_table, fitted_groups, interpolate
from fit import fit_group, load, model_zin
from nec_model import C

SWEEP = "return_height_sweep.npz"
SOIL = "average"


def load_return_height():
    d = np.load(SWEEP, allow_pickle=False)
    return d, d["resistance"] + 1j * d["reactance"]


def groups(d):
    """Every (return height, frequency, antenna height) with usable data.

    Skips the degenerate case where the return sits at the antenna's own
    height, which leaves no vertical drop to model.
    """
    for rh, freq, height in itertools.product(
        np.unique(d["return_height_m"]),
        np.unique(d["freq_hz"]),
        np.unique(d["height_m"]),
    ):
        if height <= rh:
            continue
        sel = (
            (d["return_height_m"] == rh)
            & (d["freq_hz"] == freq)
            & (d["height_m"] == height)
        )
        if sel.any():
            yield rh, freq, height, sel


if __name__ == "__main__":
    table, _ = None, None
    base_d, base_z = load()
    soils = list(base_d["soil_names"])
    table = build_table(fitted_groups(base_d, base_z), len(soils))
    soil_index = soils.index(SOIL)

    d, z = load_return_height()

    print("AGREEMENT: shipped table (fitted at a 5 cm return) vs return height")
    print(f"{'return h m':>11} {'median':>8} {'90th':>8} {'worst':>8}")
    for rh in np.unique(d["return_height_m"]):
        factors = []
        for rh_, freq, height, sel in groups(d):
            if rh_ != rh:
                continue
            wavelength_m = C / freq
            alpha_a, ka, alpha_r, vf_r, kr = interpolate(
                table, soil_index, height / wavelength_m
            )
            model = model_zin(
                (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
                d["ratio"][sel] * wavelength_m,
                height + d["return_m"][sel],
                wavelength_m,
            )
            err = np.log(np.abs(model)) - np.log(np.abs(z[sel]))
            factors.append(np.exp(np.sqrt(np.mean(err**2))))
        f = np.array(factors)
        print(
            f"{rh:11.2f} x{np.median(f):7.2f} x{np.percentile(f, 90):7.2f} "
            f"x{f.max():7.2f}"
        )

    print("\nDEPENDENCE: refitted per return height, median over groups")
    names = ("alpha_a", "vf_a", "ka", "alpha_r", "vf_r", "kr")
    print(
        f"{'return h m':>11} " + " ".join(f"{n:>9}" for n in names) + f" {'x err':>7}"
    )
    for rh in np.unique(d["return_height_m"]):
        rows, errs = [], []
        for rh_, freq, height, sel in groups(d):
            if rh_ != rh:
                continue
            wavelength_m = C / freq
            params, factor, _ = fit_group(
                d["ratio"][sel] * wavelength_m,
                height + d["return_m"][sel],
                wavelength_m,
                z[sel],
            )
            rows.append(params)
            errs.append(factor)
        med = np.median(np.array(rows), axis=0)
        print(
            f"{rh:11.2f} "
            + " ".join(f"{v:9.4f}" for v in med)
            + f" x{np.median(errs):6.2f}"
        )
