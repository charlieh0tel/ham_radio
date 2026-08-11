"""Does the segment grading at the source junction change the answer?

`nec_model._segments` applies MIN_SEGMENTS per wire independently, so a
short antenna and a long drop can meet at the feedpoint with very
different segment lengths -- 9:1 at 28.85 MHz with a short wire and a
tall mast.  NEC-2 matches currents across a junction assuming comparable
segments, and the source sits on the segment next to it, which is the
classic place for that assumption to cost accuracy.

Two things are measured, because they are different questions:

  grading   the same geometry solved with per-wire segmentation and with
            one common segment length, which removes the mismatch
  converged both of those refined together, so a difference that is only
            coarseness shows up as one that closes

A difference that survives refinement is a real modelling error and the
sweeps need re-running.  One that closes is coarseness, and the fitted
coefficients absorbed it.
"""

import numpy as np
from PyNEC import nec_context

from nec_model import C, GROUNDS, RETURN_HEIGHT_M, WIRE_RADIUS_M

FT = 0.3048
SOIL = "average"

#: Geometries chosen to span the grading ratio rather than to be typical:
#: a short wire on a high mast at 10 m is the worst case the sweep contains.
CASES = (
    ("short wire, high mast", 20.0, 25.0, 7.62, 28.85e6),
    ("default site", 84.0, 30.0, 25.0, 14.175e6),
    ("long wire, low mast", 200.0, 10.0, 25.0, 7.15e6),
    ("160 m, low", 120.0, 10.0, 25.0, 1.9e6),
)

SEG_PER_LAMBDA = (20, 40, 80)


def zin(length_m, freq_hz, height_m, return_m, seg_per_lambda, matched):
    """Feedpoint Z, segmented per wire or with one common segment length.

    matched=False reproduces nec_model: each wire gets its own count with a
    floor of 9, so short wires are finely divided and long ones coarsely.
    matched=True gives every wire the same target segment length, so the
    junction sees comparable segments on all three.
    """
    wavelength_m = C / freq_hz
    drop_m = height_m - RETURN_HEIGHT_M
    spans = (length_m, drop_m, return_m)
    if matched:
        target = min(spans) / max(
            1, int(np.ceil(seg_per_lambda * min(spans) / wavelength_m))
        )
        counts = [max(1, int(round(span / target))) for span in spans]
    else:
        counts = [
            max(int(np.ceil(seg_per_lambda * span / wavelength_m)), 9) for span in spans
        ]
    counts = [n + 1 if n % 2 == 0 else n for n in counts]

    ctx = nec_context()
    geo = ctx.get_geometry()
    geo.wire(1, counts[0], 0, 0, height_m, length_m, 0, height_m, WIRE_RADIUS_M, 1, 1)
    geo.wire(2, counts[1], 0, 0, height_m, 0, 0, RETURN_HEIGHT_M, WIRE_RADIUS_M, 1, 1)
    geo.wire(
        3,
        counts[2],
        0,
        0,
        RETURN_HEIGHT_M,
        return_m,
        0,
        RETURN_HEIGHT_M,
        WIRE_RADIUS_M,
        1,
        1,
    )
    ctx.geometry_complete(1)
    eps, sigma = GROUNDS[SOIL]
    ctx.gn_card(2, 0, eps, sigma, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0], counts


def grading_ratio(length_m, freq_hz, height_m, return_m, seg_per_lambda=20):
    """Longest segment over shortest, across the three wires."""
    wavelength_m = C / freq_hz
    spans = (length_m, height_m - RETURN_HEIGHT_M, return_m)
    counts = [max(int(np.ceil(seg_per_lambda * s / wavelength_m)), 9) for s in spans]
    counts = [n + 1 if n % 2 == 0 else n for n in counts]
    lengths = [s / n for s, n in zip(spans, counts)]
    return max(lengths) / min(lengths)


if __name__ == "__main__":
    print("grading at 20 segments per wavelength, and what removing it costs")
    print(
        f"{'case':>22} {'ratio':>6} {'seg/lam':>8} "
        f"{'per-wire':>10} {'matched':>10} {'diff':>7}"
    )
    for name, length_ft, height_ft, return_ft, freq in CASES:
        length_m, height_m, return_m = (length_ft * FT, height_ft * FT, return_ft * FT)
        ratio = grading_ratio(length_m, freq, height_m, return_m)
        for spl in SEG_PER_LAMBDA:
            a, _ = zin(length_m, freq, height_m, return_m, spl, matched=False)
            b, _ = zin(length_m, freq, height_m, return_m, spl, matched=True)
            diff = abs(abs(b) - abs(a)) / abs(a)
            label = name if spl == SEG_PER_LAMBDA[0] else ""
            shown = f"{ratio:6.1f}" if spl == SEG_PER_LAMBDA[0] else " " * 6
            print(
                f"{label:>22} {shown} {spl:8d} "
                f"{abs(a):10.1f} {abs(b):10.1f} {100 * diff:6.1f}%"
            )
