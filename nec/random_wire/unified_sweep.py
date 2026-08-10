"""The sweep the coefficients should have come from: every axis at once.

sweep.py covered antenna height and soil at one return height.
return_height_sweep.py covered return height at one soil.  Neither can
produce a table indexed on both, and return height needs one: it breaks
the shipped bound past about 15 cm, and the return line's own parameters
absorb it cleanly, so it is an axis rather than a caveat.

Return *length* stays a model input rather than a table axis, because the
two-line form already takes it as the return line's length.  It is swept
only so the fit has something to fit against.
"""

import itertools
import time
from multiprocessing import Pool

import numpy as np

from nec_model import C, GROUNDS
from return_height_sweep import zin

FREQS_HZ = (1.9e6, 7.15e6, 14.175e6, 28.85e6)
HEIGHTS_M = (3.0, 5.0, 10.0, 15.0, 25.0)
RETURN_HEIGHTS_M = (0.01, 0.05, 0.15, 0.5, 1.0, 2.0)
RETURNS_M = (4.0, 7.62, 20.0, 40.0)

RATIO_MIN, RATIO_MAX, RATIO_STEP = 0.05, 4.0, 0.025

OUTPUT = "unified_sweep.npz"


def _grid():
    ratios = np.arange(RATIO_MIN, RATIO_MAX + RATIO_STEP / 2, RATIO_STEP)
    return [
        point
        for point in itertools.product(
            sorted(GROUNDS), FREQS_HZ, HEIGHTS_M, RETURN_HEIGHTS_M, RETURNS_M, ratios
        )
        # The return cannot sit at or above the wire it hangs below; that
        # leaves no vertical drop to model.
        if point[3] < point[2]
    ]


def _run(point):
    soil, freq_hz, height_m, return_height_m, return_m, ratio = point
    length_m = ratio * (C / freq_hz)
    try:
        z = zin(length_m, freq_hz, height_m, return_m, return_height_m, soil=soil)
        return z.real, z.imag
    except Exception:
        return np.nan, np.nan


if __name__ == "__main__":
    grid = _grid()
    soils = sorted(GROUNDS)
    print(
        f"{len(grid)} points: {len(soils)} soils x {len(FREQS_HZ)} freqs x "
        f"{len(HEIGHTS_M)} heights x {len(RETURN_HEIGHTS_M)} return heights x "
        f"{len(RETURNS_M)} return lengths"
    )
    start = time.time()
    with Pool() as pool:
        results = pool.map(_run, grid, chunksize=64)
    np.savez_compressed(
        OUTPUT,
        soil=np.array([soils.index(p[0]) for p in grid], dtype=np.int8),
        freq_hz=np.array([p[1] for p in grid]),
        height_m=np.array([p[2] for p in grid]),
        return_height_m=np.array([p[3] for p in grid]),
        return_m=np.array([p[4] for p in grid]),
        ratio=np.array([p[5] for p in grid]),
        resistance=np.array([r[0] for r in results]),
        reactance=np.array([r[1] for r in results]),
        soil_names=np.array(soils),
    )
    bad = sum(1 for r in results if np.isnan(r[0]))
    print(f"done in {time.time() - start:.1f} s, {bad} failed, wrote {OUTPUT}")
