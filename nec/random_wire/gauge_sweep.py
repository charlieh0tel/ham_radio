"""Does conductor gauge matter, and do the #14 coefficients survive it?

The main sweep ran entirely at #14 AWG, so `a/lambda` is the one planned
axis never executed and every fitted coefficient has seen one diameter.
Two separate questions follow, and they have different answers:

  dependence  do the fitted coefficients move with gauge?
  agreement   does the shipped table, fitted at #14, still predict other
              gauges within its stated bound?

Agreement is the one that matters for the page.  Coefficients could drift
with gauge while the model still predicts adequately, because Schelkunoff's
Z0 already carries a logarithmic diameter term.

Grid is reduced against sweep.py: one soil, fewer heights and returns,
since the question is a single axis rather than the whole surface.
"""

import itertools
import time
from multiprocessing import Pool

import numpy as np

from nec_model import C, end_fed_zin

#: Radii in metres for common antenna wire.  #12 through #22 spans what
#: anyone actually hangs, a factor of 3.2 in diameter.
GAUGES = {
    "12": 2.053e-3 / 2,
    "14": 1.628e-3 / 2,
    "18": 1.024e-3 / 2,
    "22": 0.644e-3 / 2,
}

FREQS_HZ = (1.9e6, 7.15e6, 14.175e6, 28.85e6)
HEIGHTS_M = (3.0, 10.0, 25.0)
RETURNS_M = (4.0, 7.62, 20.0)
SOIL = "average"

RATIO_MIN, RATIO_MAX, RATIO_STEP = 0.05, 4.0, 0.025

OUTPUT = "gauge_sweep.npz"


def _grid():
    ratios = np.arange(RATIO_MIN, RATIO_MAX + RATIO_STEP / 2, RATIO_STEP)
    return list(
        itertools.product(sorted(GAUGES), FREQS_HZ, HEIGHTS_M, RETURNS_M, ratios)
    )


def _run(point):
    gauge, freq_hz, height_m, return_m, ratio = point
    length_m = ratio * (C / freq_hz)
    try:
        z = end_fed_zin(
            length_m,
            freq_hz,
            height_m,
            return_m,
            ground=SOIL,
            radius_m=GAUGES[gauge],
        )
        return z.real, z.imag
    except Exception:
        return np.nan, np.nan


if __name__ == "__main__":
    grid = _grid()
    print(f"{len(grid)} points over {len(GAUGES)} gauges")
    start = time.time()
    with Pool() as pool:
        results = pool.map(_run, grid, chunksize=64)
    gauges = sorted(GAUGES)
    np.savez_compressed(
        OUTPUT,
        gauge=np.array([gauges.index(p[0]) for p in grid], dtype=np.int8),
        radius_m=np.array([GAUGES[p[0]] for p in grid]),
        freq_hz=np.array([p[1] for p in grid]),
        height_m=np.array([p[2] for p in grid]),
        return_m=np.array([p[3] for p in grid]),
        ratio=np.array([p[4] for p in grid]),
        resistance=np.array([r[0] for r in results]),
        reactance=np.array([r[1] for r in results]),
        gauge_names=np.array(gauges),
    )
    bad = sum(1 for r in results if np.isnan(r[0]))
    print(f"done in {time.time() - start:.1f} s, {bad} failed, wrote {OUTPUT}")
