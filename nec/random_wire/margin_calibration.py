"""What does the classical margin actually buy, in ohms?

The classical mode keeps a length clear of `n * lambda/2` by a percentage
of a half wavelength, defaulting to 8.  That number has never been
justified against anything: the TODO has carried "validate the keep-out
widths" and "derive marginPct from a user-set |Z|max" since before there
was a model to ask.

There is one now, and the two modes agree about where the bad lengths
are, so the model can price the margin.  Two questions:

  what does a margin buy   the worst |Z| still reachable just outside a
                           zone of that width
  what does a limit cost   the margin needed to hold |Z| under a stated
                           figure, and what that leaves of the axis

The second is the useful direction, because a user can state an
impedance their tuner will reach, and cannot state a percentage.
"""

import numpy as np

from coefficients import VF_A, build_table, fitted_groups, interpolate
from fit import load, model_zin
from nec_model import C

FT = 0.3048

#: The page's default site, since the answer depends on it.
SITE_HEIGHT_M = 9.144
SITE_RETURN_M = 7.62
SITE_SOIL = "average"

BANDS = {
    "80m": (3.5e6, 4.0e6),
    "40m": (7.0e6, 7.3e6),
    "20m": (14.0e6, 14.35e6),
    "15m": (21.0e6, 21.45e6),
    "10m": (28.0e6, 29.7e6),
}

MARGINS_PCT = (0, 2, 4, 6, 8, 10, 12, 15)
Z_LIMITS = (600, 1000, 1500, 2500, 4000)
SAMPLES_PER_BAND = 9
MAX_LEN_M = 60.0
STEP_M = 0.02


def worst_z(length_m, table, soil_index):
    """Largest |Z| this length shows anywhere in the selected bands."""
    worst = 0.0
    for lo, hi in BANDS.values():
        for i in range(SAMPLES_PER_BAND):
            freq = lo + (hi - lo) * i / (SAMPLES_PER_BAND - 1)
            wavelength_m = C / freq
            alpha_a, ka, alpha_r, vf_r, kr = interpolate(
                table, soil_index, SITE_HEIGHT_M / wavelength_m
            )
            z = model_zin(
                (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
                np.array([length_m]),
                np.array([SITE_HEIGHT_M + SITE_RETURN_M]),
                wavelength_m,
            )[0]
            worst = max(worst, abs(z))
    return worst


def in_any_zone(length_m, margin_pct):
    """Does this length fall inside a classical keep-out zone?

    Mirrors resonanceInterval: a zone spans (n -/+ margin) half waves,
    taken at the band edge that makes it widest, and the model's own
    velocity factor is used so the comparison is like for like.
    """
    margin = margin_pct / 100.0
    for lo, hi in BANDS.values():
        shortest = (C / hi) * VF_A / 2
        longest = (C / lo) * VF_A / 2
        for n in range(1, int(MAX_LEN_M / shortest) + 2):
            if (n - margin) * shortest <= length_m <= (n + margin) * longest:
                return True
    return False


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])
    table = build_table(fitted_groups(d, z), len(soils))
    soil_index = soils.index(SITE_SOIL)

    lengths = np.arange(4.0, MAX_LEN_M, STEP_M)
    peaks = np.array([worst_z(x, table, soil_index) for x in lengths])

    print(
        f"{len(lengths)} lengths scored, {SITE_HEIGHT_M / FT:.0f} ft up, "
        f"{SITE_RETURN_M / FT:.0f} ft return, {SITE_SOIL} soil"
    )
    print(f"worst |Z| anywhere: {peaks.max():.0f} ohms\n")

    print("what a margin buys")
    print(f"{'margin %':>9} {'usable %':>9} {'worst |Z| outside':>18}")
    for margin_pct in MARGINS_PCT:
        outside = np.array([not in_any_zone(x, margin_pct) for x in lengths])
        if not outside.any():
            print(f"{margin_pct:9d} {0.0:8.1f}% {'-- nothing left --':>18}")
            continue
        print(
            f"{margin_pct:9d} {100 * outside.mean():8.1f}% {peaks[outside].max():17.0f}"
        )

    print("\nwhat a limit costs")
    print(f"{'|Z| max':>8} {'margin needed':>14} {'usable %':>9}")
    for limit in Z_LIMITS:
        needed = None
        for margin_pct in range(0, 26):
            outside = np.array([not in_any_zone(x, margin_pct) for x in lengths])
            if outside.any() and peaks[outside].max() <= limit:
                needed = (margin_pct, 100 * outside.mean())
                break
        if needed is None:
            print(f"{limit:8d} {'unreachable':>14} {'-':>9}")
        else:
            print(f"{limit:8d} {needed[0]:13d}% {needed[1]:8.1f}%")
