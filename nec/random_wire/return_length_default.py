"""Is the 25 ft return default what is condemning the published lengths?

The page defaults the return path to 25 ft.  The ARRL's own guidance says
a counterpoise should be a quarter wave at the lowest band in use, which
is about 66 ft on 80 m: the default is a quarter of that.  The sweep
already showed return length moves the feedpoint a great deal, and the
poor scores for 71 ft and 119 ft were computed at 25 ft.

So: score the published lengths, and re-derive the page's picks, across a
range of return lengths.  If the staples come good at a longer return,
the default is the problem rather than the lengths.
"""

import numpy as np

from compare_picks import (
    BANDS,
    FT,
    PUBLISHED_FT,
    SITE_HEIGHT_M,
    SITE_SOIL,
    local_minima,
    swr,
)
from coefficients import VF_A, build_table, fitted_groups, interpolate
from fit import load, model_zin
from nec_model import C

#: Return runs to try, feet.  25 is today's default; 66 is a quarter wave
#: on 80 m, the ARRL figure; 130 is a quarter wave on 160 m.
RETURNS_FT = (10, 25, 40, 66, 100, 130)

SAMPLES_PER_BAND = 9


def zin_at(length_m, freq_hz, return_m, table, soil_index):
    wavelength_m = C / freq_hz
    alpha_a, ka, alpha_r, vf_r, kr = interpolate(
        table, soil_index, SITE_HEIGHT_M / wavelength_m
    )
    return model_zin(
        (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
        np.array([length_m]),
        np.array([SITE_HEIGHT_M + return_m]),
        wavelength_m,
    )[0]


def score_at(length_m, return_m, table, soil_index):
    logs = []
    for lo, hi in BANDS.values():
        for i in range(SAMPLES_PER_BAND):
            freq = lo + (hi - lo) * i / (SAMPLES_PER_BAND - 1)
            logs.append(
                np.log(swr(zin_at(length_m, freq, return_m, table, soil_index)))
            )
    return float(np.exp(np.mean(logs)))


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])
    table = build_table(fitted_groups(d, z), len(soils))
    soil_index = soils.index(SITE_SOIL)

    print("published lengths, scored against return length (30 ft high, medium)")
    print(f"{'ft':>7} " + " ".join(f"{r:>7}" for r in RETURNS_FT))
    for pub in PUBLISHED_FT:
        row = [score_at(pub * FT, r * FT, table, soil_index) for r in RETURNS_FT]
        print(f"{pub:7.1f} " + " ".join(f"{v:7.2f}" for v in row))

    print("\nthe page's own picks, per return length")
    lengths_m = np.arange(3.0, 65.0, 0.05)
    for r in RETURNS_FT:
        scores = [score_at(x, r * FT, table, soil_index) for x in lengths_m]
        best = local_minima(lengths_m, scores, count=5)
        picks = ", ".join(f"{b[1] / FT:.0f} ft ({b[0]:.1f})" for b in best)
        gaps = [min(abs(b[1] / FT - p) for p in PUBLISHED_FT) for b in best]
        print(f"  return {r:3d} ft: {picks}")
        print(f"{'':14} median gap to a published length {np.median(gaps):.1f} ft")
