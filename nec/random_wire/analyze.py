"""Decide the fit form before fitting anything.

Hypothesis H1, the series decomposition:

    Zin(l, ret) = Za(l) + Zr(ret)

the antenna and the return path as two lines in series at the feedpoint.
If it holds, the return path earns a separate additive term and the two
can be fitted independently, which is the cheap and interpretable outcome.

Falsifiable test: under H1, Zin(l, ret_b) - Zin(l, ret_a) = Zr(ret_b) -
Zr(ret_a), which does not depend on l.  So hold f, h and soil fixed, take
that difference across a pair of return lengths, and see whether it is
constant in l.  Scatter across l that is large compared with the
difference itself falsifies H1 and means the two are coupled.
"""

import numpy as np

SWEEP = "sweep.npz"


def load():
    d = np.load(SWEEP, allow_pickle=False)
    z = d["resistance"] + 1j * d["reactance"]
    return d, z


def series_test(
    d, z, freq_hz, height_m, soil_index, ret_a, ret_b, ratio_lo=0.1, ratio_hi=2.0
):
    """Spread of Zin(ret_b) - Zin(ret_a) across antenna length."""
    base = (
        (d["freq_hz"] == freq_hz)
        & (d["height_m"] == height_m)
        & (d["soil"] == soil_index)
        & (d["ratio"] >= ratio_lo)
        & (d["ratio"] <= ratio_hi)
    )
    sel_a = base & (d["return_m"] == ret_a)
    sel_b = base & (d["return_m"] == ret_b)
    ratios_a, ratios_b = d["ratio"][sel_a], d["ratio"][sel_b]
    assert np.allclose(ratios_a, ratios_b), "grids differ"
    delta = z[sel_b] - z[sel_a]
    # Under H1 delta is constant; measure how far it actually wanders.
    spread = np.std(delta)
    return np.mean(delta), spread, np.mean(np.abs(delta))


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])
    print(f"{len(z)} points loaded, {np.isnan(z.real).sum()} NaN\n")

    print("=== H1: is the return path additive? ===")
    print("delta = Zin(ret_b) - Zin(ret_a), swept over l/lambda in 0.1-2.0")
    print("H1 holds if spread << |delta|.\n")
    print(
        f"{'f MHz':>7} {'h m':>5} {'soil':>8} {'ret_a':>6} {'ret_b':>6} "
        f"{'mean delta':>20} {'spread':>10} {'spread/|delta|':>15}"
    )
    for freq in np.unique(d["freq_hz"]):
        for height in (3.0, 10.0, 20.0):
            for si, soil in enumerate(soils):
                for ret_a, ret_b in ((2.0, 7.62), (7.62, 20.0)):
                    m, s, a = series_test(d, z, freq, height, si, ret_a, ret_b)
                    print(
                        f"{freq / 1e6:7.2f} {height:5.0f} {soil:>8} "
                        f"{ret_a:6.2f} {ret_b:6.1f} {m:>20.0f} "
                        f"{s:10.0f} {s / a:15.2f}"
                    )
