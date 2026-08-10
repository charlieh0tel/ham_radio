"""Full NEC sweep behind the fitted coefficients.

Axes are dimensionless where the physics is scale invariant and physical
where it is not.  NEC geometry scales with wavelength, but the ground does
not: the soil's complex permittivity, eps - j*sigma/(omega*eps0), is a
function of frequency, so a handful of frequencies spanning HF is swept
rather than one.  Height and return length are held in metres so every
point in the grid is an installation someone could actually build.

Output is a compressed .npz of R and X over the grid, which fit.py reads.
"""

import itertools
import time
from multiprocessing import Pool

import numpy as np

from nec_model import C, GROUNDS, end_fed_zin

#: Four frequencies spanning HF.  More would only resolve the soil's
#: frequency dependence, which is smooth; the rest of the problem scales.
FREQS_HZ = (1.9e6, 7.15e6, 14.175e6, 28.85e6)

#: Heights someone might actually hang a wire at, metres.
HEIGHTS_M = (2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0)

#: Return-path runs, metres.  7.62 m is the 25 ft default.
RETURNS_M = (2.0, 4.0, 7.62, 12.0, 20.0, 30.0, 45.0)

#: Antenna length in wavelengths.  Step resolves the half-wave peaks, which
#: are the whole point; 4 wavelengths covers 160 m band lengths up on 10 m.
RATIO_MIN, RATIO_MAX, RATIO_STEP = 0.05, 4.0, 0.025

OUTPUT = "sweep.npz"


def _grid():
    ratios = np.arange(RATIO_MIN, RATIO_MAX + RATIO_STEP / 2, RATIO_STEP)
    return list(
        itertools.product(FREQS_HZ, HEIGHTS_M, RETURNS_M, sorted(GROUNDS), ratios)
    )


def _run(point):
    """One NEC solve.  Returns NaN rather than dying on a bad geometry."""
    freq_hz, height_m, return_m, soil, ratio = point
    length_m = ratio * (C / freq_hz)
    try:
        z = end_fed_zin(length_m, freq_hz, height_m, return_m, ground=soil)
        return z.real, z.imag
    except Exception:
        return np.nan, np.nan


if __name__ == "__main__":
    grid = _grid()
    print(
        f"{len(grid)} points over "
        f"{len(FREQS_HZ)} freqs x {len(HEIGHTS_M)} heights x "
        f"{len(RETURNS_M)} returns x {len(GROUNDS)} soils x "
        f"{len(grid) // (len(FREQS_HZ) * len(HEIGHTS_M) * len(RETURNS_M) * len(GROUNDS))} lengths"
    )

    start = time.time()
    with Pool() as pool:
        results = pool.map(_run, grid, chunksize=64)
    elapsed = time.time() - start

    soils = sorted(GROUNDS)
    np.savez_compressed(
        OUTPUT,
        freq_hz=np.array([p[0] for p in grid]),
        height_m=np.array([p[1] for p in grid]),
        return_m=np.array([p[2] for p in grid]),
        soil=np.array([soils.index(p[3]) for p in grid], dtype=np.int8),
        ratio=np.array([p[4] for p in grid]),
        resistance=np.array([r[0] for r in results]),
        reactance=np.array([r[1] for r in results]),
        soil_names=np.array(soils),
    )
    bad = sum(1 for r in results if np.isnan(r[0]))
    print(f"done in {elapsed:.1f} s, {bad} failed, wrote {OUTPUT}")
