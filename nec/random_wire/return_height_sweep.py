"""Sweep the return path's height, the largest unmodelled term.

geometry_check.py found that raising the return from 5 cm to 1-2 m moves
the feedpoint by up to 4.6x -- further than the quoted bound, and further
than antenna height, soil or gauge move it.  Every shipped coefficient
was fitted at one return height, standing for a feedline or counterpoise
lying on the soil.

The hypothesis worth testing is cheap: return height is a property of the
*return line*, and that line already has its own fitted alpha, velocity
factor and Z0 scale.  If those three absorb it smoothly, return height
becomes another axis to tabulate against rather than a new term, and the
page can offer it as a control.

Antenna height is reduced to four values and soil held at medium, since
the question is one axis rather than the whole surface.
"""

import itertools
import time
from multiprocessing import Pool

import numpy as np
from PyNEC import nec_context

from nec_model import C, GROUNDS, WIRE_RADIUS_M, _segments

#: Return heights, metres.  0.01 is lying on the soil, 3 m is a properly
#: elevated counterpoise; the shipped sweep used 0.05 throughout.
RETURN_HEIGHTS_M = (0.01, 0.05, 0.15, 0.5, 1.0, 2.0, 3.0)

FREQS_HZ = (1.9e6, 7.15e6, 14.175e6, 28.85e6)
HEIGHTS_M = (3.0, 7.0, 12.0, 20.0)
RETURNS_M = (4.0, 7.62, 20.0)
SOIL = "average"

RATIO_MIN, RATIO_MAX, RATIO_STEP = 0.05, 4.0, 0.025

OUTPUT = "return_height_sweep.npz"


def zin(
    length_m,
    freq_hz,
    height_m,
    return_len_m,
    return_height_m,
    radius_m=WIRE_RADIUS_M,
    soil=SOIL,
):
    """Feedpoint Z with the return run at an arbitrary height.

    Same geometry as nec_model.end_fed_zin, with the return's height freed
    rather than fixed at RETURN_HEIGHT_M.
    """
    wavelength_m = C / freq_hz
    ctx = nec_context()
    geo = ctx.get_geometry()
    geo.wire(
        1,
        _segments(length_m, wavelength_m),
        0,
        0,
        height_m,
        length_m,
        0,
        height_m,
        radius_m,
        1,
        1,
    )
    geo.wire(
        2,
        _segments(height_m, wavelength_m),
        0,
        0,
        height_m,
        0,
        0,
        return_height_m,
        radius_m,
        1,
        1,
    )
    geo.wire(
        3,
        _segments(return_len_m, wavelength_m),
        0,
        0,
        return_height_m,
        return_len_m,
        0,
        return_height_m,
        radius_m,
        1,
        1,
    )
    ctx.geometry_complete(1)
    eps, sigma = GROUNDS[soil]
    ctx.gn_card(2, 0, eps, sigma, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


def _grid():
    ratios = np.arange(RATIO_MIN, RATIO_MAX + RATIO_STEP / 2, RATIO_STEP)
    return list(
        itertools.product(RETURN_HEIGHTS_M, FREQS_HZ, HEIGHTS_M, RETURNS_M, ratios)
    )


def _run(point):
    return_height_m, freq_hz, height_m, return_m, ratio = point
    length_m = ratio * (C / freq_hz)
    try:
        z = zin(length_m, freq_hz, height_m, return_m, return_height_m)
        return z.real, z.imag
    except Exception:
        return np.nan, np.nan


if __name__ == "__main__":
    grid = _grid()
    print(f"{len(grid)} points over {len(RETURN_HEIGHTS_M)} return heights")
    start = time.time()
    with Pool() as pool:
        results = pool.map(_run, grid, chunksize=64)
    np.savez_compressed(
        OUTPUT,
        return_height_m=np.array([p[0] for p in grid]),
        freq_hz=np.array([p[1] for p in grid]),
        height_m=np.array([p[2] for p in grid]),
        return_m=np.array([p[3] for p in grid]),
        ratio=np.array([p[4] for p in grid]),
        resistance=np.array([r[0] for r in results]),
        reactance=np.array([r[1] for r in results]),
    )
    bad = sum(1 for r in results if np.isnan(r[0]))
    print(f"done in {time.time() - start:.1f} s, {bad} failed, wrote {OUTPUT}")
