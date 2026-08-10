"""Fit the unified sweep, and choose the return-height axis by measuring it.

The shipped table is indexed on h/lambda and soil, fitted at one return
height.  Return height needs to join it: the table breaks past about 15 cm
of it, and the return line's own parameters absorb it cleanly.

Which variable to index on is a question rather than a choice.  Height uses
h/lambda because the physics is scale invariant there.  The return lies
close to a lossy half-space, where the loading depends on rh/lambda, so the
same argument says rh/lambda -- but the sweep holds return height in metres
because that is what an installation has, and the two disagree by more than
a decade across HF.  Fit per group, then look.
"""

import itertools

import numpy as np

from fit import PARAM_NAMES, fit_group
from nec_model import C

SWEEP = "unified_sweep.npz"


def load_unified():
    d = np.load(SWEEP, allow_pickle=False)
    return d, d["resistance"] + 1j * d["reactance"]


def groups(d):
    """Every (soil, frequency, height, return height) combination present."""
    for si, freq, height, return_height in itertools.product(
        np.unique(d["soil"]),
        np.unique(d["freq_hz"]),
        np.unique(d["height_m"]),
        np.unique(d["return_height_m"]),
    ):
        sel = (
            (d["soil"] == si)
            & (d["freq_hz"] == freq)
            & (d["height_m"] == height)
            & (d["return_height_m"] == return_height)
        )
        if sel.any():
            yield si, freq, height, return_height, sel


def fit_all(d, z):
    """Fitted parameters for every group, with the axes they might index on."""
    rows = []
    for si, freq, height, return_height, sel in groups(d):
        wavelength_m = C / freq
        params, factor, _ = fit_group(
            d["ratio"][sel] * wavelength_m,
            height + d["return_m"][sel],
            wavelength_m,
            z[sel],
        )
        rows.append(
            {
                "soil": int(si),
                "h_over_lam": height / wavelength_m,
                "rh_over_lam": return_height / wavelength_m,
                "return_height_m": return_height,
                "params": params,
                "factor": factor,
            }
        )
    return rows


def spearman(x, y):
    """Rank correlation, which does not assume the relation is linear."""
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


if __name__ == "__main__":
    d, z = load_unified()
    rows = fit_all(d, z)
    params = np.array([r["params"] for r in rows])
    factors = np.array([r["factor"] for r in rows])

    print(f"{len(rows)} groups fitted")
    print(
        f"  per-group error: median x{np.median(factors):.2f}  "
        f"90th x{np.percentile(factors, 90):.2f}  worst x{factors.max():.2f}"
    )

    print("\nwhich axis does each parameter track?  (rank correlation)")
    print(f"{'parameter':>12} {'h/lambda':>10} {'rh/lambda':>11} {'rh metres':>11}")
    for i, name in enumerate(PARAM_NAMES):
        if name == "vf_a":
            continue
        print(
            f"{name:>12} "
            f"{spearman([r['h_over_lam'] for r in rows], params[:, i]):10.2f} "
            f"{spearman([r['rh_over_lam'] for r in rows], params[:, i]):11.2f} "
            f"{spearman([r['return_height_m'] for r in rows], params[:, i]):11.2f}"
        )

    print("\nreturn-line parameters against return height, medians")
    print(
        f"{'rh m':>7} {'rh/lam range':>16} "
        + " ".join(f"{n:>9}" for n in PARAM_NAMES[3:])
    )
    for rh in np.unique([r["return_height_m"] for r in rows]):
        mine = [r for r in rows if r["return_height_m"] == rh]
        block = np.array([r["params"] for r in mine])
        span = [r["rh_over_lam"] for r in mine]
        print(
            f"{rh:7.2f} {min(span):7.5f}-{max(span):.5f} "
            + " ".join(f"{np.median(block[:, 3 + j]):9.4f}" for j in range(3))
        )
