"""Where does the two-line model fail, and as a function of what?

The worst groups are all at low h/lambda, which finding 7 attributes to
mutual coupling between the wire and its return.  Before adding a term
for that, look at the shape of the error: a coupling term has to change
how the model depends on l and on the return length, not merely its
level, since the per-group fit already absorbs any level offset.

Prints the log-magnitude residual binned against each candidate
variable, worst groups first.
"""

import itertools

import numpy as np

from fit import fit_group, load, model_zin
from nec_model import C


def group_residual(d, z, freq_hz, height_m, soil_index):
    """Fitted residual for one group, with the variables it might depend on."""
    sel = (
        (d["freq_hz"] == freq_hz)
        & (d["height_m"] == height_m)
        & (d["soil"] == soil_index)
    )
    wavelength_m = C / freq_hz
    length_m = d["ratio"][sel] * wavelength_m
    total_return_m = height_m + d["return_m"][sel]
    params, factor, _ = fit_group(length_m, total_return_m, wavelength_m, z[sel])
    model = model_zin(params, length_m, total_return_m, wavelength_m)
    return {
        "log_err": np.log(np.abs(model)) - np.log(np.abs(z[sel])),
        "ratio": d["ratio"][sel],
        "return_lam": d["return_m"][sel] / wavelength_m,
        "factor": factor,
    }


def binned(x, y, edges):
    """Mean of y in each bin of x, as a printable row."""
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (x >= lo) & (x < hi)
        out.append(np.mean(y[m]) if m.any() else np.nan)
    return out


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])

    groups = []
    for freq, height, si in itertools.product(
        np.unique(d["freq_hz"]), np.unique(d["height_m"]), range(len(soils))
    ):
        r = group_residual(d, z, freq, height, si)
        groups.append((r["factor"], freq, height, si, r))
    groups.sort(key=lambda g: -g[0])

    ratio_edges = np.array([0.05, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.01])
    ret_edges = np.array([0.0, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0, 2.0])

    print("worst six groups, mean log-magnitude error by antenna length")
    print(
        f"{'f MHz':>6} {'h m':>4} {'soil':>8} {'h/lam':>7} "
        + " ".join(f"{e:>6.2f}" for e in ratio_edges[:-1])
    )
    for factor, freq, height, si, r in groups[:6]:
        row = binned(r["ratio"], r["log_err"], ratio_edges)
        print(
            f"{freq / 1e6:6.2f} {height:4.0f} {soils[si]:>8} "
            f"{height / (C / freq):7.4f} " + " ".join(f"{v:6.2f}" for v in row)
        )

    print("\nsame groups, by return length in wavelengths")
    print(
        f"{'f MHz':>6} {'h m':>4} {'soil':>8} {'h/lam':>7} "
        + " ".join(f"{e:>6.2f}" for e in ret_edges[:-1])
    )
    for factor, freq, height, si, r in groups[:6]:
        row = binned(r["return_lam"], r["log_err"], ret_edges)
        print(
            f"{freq / 1e6:6.2f} {height:4.0f} {soils[si]:>8} "
            f"{height / (C / freq):7.4f} " + " ".join(f"{v:6.2f}" for v in row)
        )

    print("\nerror factor against h/lambda, all groups")
    h_over_lam = np.array([g[2] / (C / g[1]) for g in groups])
    factors = np.array([g[0] for g in groups])
    edges = np.array([0.0, 0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 3.0])
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (h_over_lam >= lo) & (h_over_lam < hi)
        if m.any():
            print(
                f"  h/lam {lo:5.2f}-{hi:4.2f}: {m.sum():3d} groups, "
                f"median x{np.median(factors[m]):.2f}, worst x{factors[m].max():.2f}"
            )
