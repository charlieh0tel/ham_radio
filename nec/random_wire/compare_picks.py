"""Did swapping the model move the lengths the page recommends?

Recommending lengths is what the page is for, so replacing the impedance
model is exactly the change that could move them.  The old model's picks
were checked against the published random-wire tables; this checks the
new ones the same way, and against the old.

Mirrors the page's scoring: geometric mean of SWR at the radio through
the transformer, sampled across each selected band, offering the local
minima best first.
"""

import numpy as np

from coefficients import VF_A, build_table, fitted_groups, interpolate
from fit import load, model_zin, schelkunoff_z0
from nec_model import C

FT = 0.3048

#: US band edges in hertz, the page's default selection.
BANDS = {
    "80m": (3.5e6, 4.0e6),
    "40m": (7.0e6, 7.3e6),
    "20m": (14.0e6, 14.35e6),
    "15m": (21.0e6, 21.45e6),
    "10m": (28.0e6, 29.7e6),
}

#: Lengths the published tables offer, feet.  The AB3AP list and its
#: relatives, which is what the page was checked against before.
PUBLISHED_FT = (29, 35.5, 41, 58, 71, 84, 107, 119, 148, 203)

SAMPLES_PER_BAND = 9
UNUN = 9.0
Z_SYSTEM = 50.0
HALF_WAVE_OHMS = 2450.0
OLD_VF = 0.95

#: The site the new model is asked about: the page's defaults.
SITE_HEIGHT_M = 9.144
SITE_RETURN_M = 7.62
SITE_SOIL = "average"


def old_zin(length_m, freq_hz):
    """The single anchored line the page used to ship."""
    z0 = schelkunoff_z0(length_m)
    wavelength_m = (C / freq_hz) * OLD_VF
    quarter = z0 * z0 / (2 * HALF_WAVE_OHMS)
    alpha = np.arctanh(quarter / z0) / (wavelength_m / 4)
    beta = 2 * np.pi / wavelength_m
    return z0 / np.tanh(complex(alpha * length_m, beta * length_m))


def new_zin(length_m, freq_hz, table, soil_index):
    """The fitted two-line model, at the page's default site."""
    wavelength_m = C / freq_hz
    alpha_a, ka, alpha_r, vf_r, kr = interpolate(
        table, soil_index, SITE_HEIGHT_M / wavelength_m
    )
    return model_zin(
        (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
        np.array([length_m]),
        np.array([SITE_HEIGHT_M + SITE_RETURN_M]),
        wavelength_m,
    )[0]


def swr(z, ratio=UNUN):
    g = abs((z / ratio - Z_SYSTEM) / (z / ratio + Z_SYSTEM))
    return (1 + g) / (1 - g) if g < 1 else 1e6


def score(length_m, zin):
    """Geometric mean SWR across the bands, as the page computes it."""
    logs = []
    for lo, hi in BANDS.values():
        for i in range(SAMPLES_PER_BAND):
            freq = lo + (hi - lo) * i / (SAMPLES_PER_BAND - 1)
            logs.append(np.log(swr(zin(length_m, freq))))
    return float(np.exp(np.mean(logs)))


def short_limit_m():
    """The page will not offer a wire shorter than a quarter wave on the
    lowest selected band, so neither does this."""
    lowest = min(lo for lo, _ in BANDS.values())
    return (C / lowest) / 4.0


def local_minima(lengths_m, scores, count=8):
    """Strict local minima, best first, as the page offers them."""
    floor_m = short_limit_m()
    out = []
    for i in range(1, len(scores) - 1):
        if (
            scores[i] < scores[i - 1]
            and scores[i] <= scores[i + 1]
            and lengths_m[i] >= floor_m
        ):
            out.append((scores[i], lengths_m[i]))
    out.sort()
    return out[:count]


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])
    table = build_table(fitted_groups(d, z), len(soils))
    soil_index = soils.index(SITE_SOIL)

    lengths_m = np.arange(3.0, 65.0, 0.05)
    old_scores = [score(x, old_zin) for x in lengths_m]
    new_scores = [
        score(x, lambda x_, f: new_zin(x_, f, table, soil_index)) for x in lengths_m
    ]

    print("recommended lengths, feet, best first")
    print(f"{'old model':>28} | {'new model':>28}")
    old_best = local_minima(lengths_m, old_scores)
    new_best = local_minima(lengths_m, new_scores)
    for i in range(max(len(old_best), len(new_best))):
        left = (
            f"{old_best[i][1] / FT:8.1f} ft  SWR {old_best[i][0]:5.2f}"
            if i < len(old_best)
            else ""
        )
        right = (
            f"{new_best[i][1] / FT:8.1f} ft  SWR {new_best[i][0]:5.2f}"
            if i < len(new_best)
            else ""
        )
        print(f"{left:>28} | {right:>28}")

    print("\npublished lengths, scored by each model")
    print(f"{'ft':>7} {'old SWR':>9} {'new SWR':>9}")
    for ft in PUBLISHED_FT:
        m = ft * FT
        print(
            f"{ft:7.1f} {score(m, old_zin):9.2f} "
            f"{score(m, lambda x_, f: new_zin(x_, f, table, soil_index)):9.2f}"
        )

    print("\nhow close is each model's best pick to a published length?")
    for name, best in (("old", old_best), ("new", new_best)):
        gaps = [min(abs(b[1] / FT - p) for p in PUBLISHED_FT) for b in best]
        print(
            f"  {name}: median gap {np.median(gaps):.1f} ft, "
            f"picks within 5 ft of a published length: "
            f"{sum(1 for g in gaps if g <= 5)}/{len(gaps)}"
        )
