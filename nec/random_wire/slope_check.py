"""Does a sloper behave like a flat top at the same free-end height?

The model assumes a horizontal wire fed at height h, with the coax
dropping from the feedpoint to the ground.  A sloper is fed near the
ground and rises to a high free end, which differs in two ways at once:
the wire is not horizontal, and the feed is at the other end of it.

Compared against the flat model at two candidate equivalent heights: the
free-end height, and the mean height of the slanting wire.
"""

import re
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from nec_model import C, GROUNDS, WIRE_RADIUS_M, _segments, end_fed_deck

SCI = re.compile(r"[-+]?\d*\.?\d+[Ee][-+]?\d+")
NEC4 = "/usr/bin/nec4d42"
SOIL, RETURN_M, FEED_Z, RH = "average", 7.62, 1.5, 0.05
RATIOS = np.arange(0.15, 1.55, 0.05)


def spread(ratios):
    """Geometric median and worst of a set of ratios, as factors."""
    log = np.abs(np.log(ratios))
    return f"med x{np.exp(np.median(log)):.2f} worst x{np.exp(log.max()):.2f}"


def run(deck, work):
    src, out = Path(work) / "i.nec", Path(work) / "o.txt"
    src.write_text(deck)
    subprocess.run(
        [NEC4, str(src), str(out)], capture_output=True, check=True, cwd=work
    )
    t = out.read_text()
    for i, l in enumerate(t.splitlines()):
        if "(WATTS)" in l:
            for r in t.splitlines()[i + 1 :]:
                v = SCI.findall(r)
                if len(v) >= 6:
                    return complex(float(v[4]), float(v[5]))
    return complex(np.nan, np.nan)


def sloper_deck(slant_m, freq, apex_z, ret_m):
    """Fed at FEED_Z near the ground, rising to apex_z at the far end."""
    lam, (eps, sig) = C / freq, GROUNDS[SOIL]
    dz = apex_z - FEED_Z
    if slant_m <= dz:
        return None
    run_x = float(np.sqrt(slant_m**2 - dz**2))
    w = [
        f"GW 1 {_segments(slant_m, lam)} 0 0 {FEED_Z:.6g} {run_x:.6g} 0 {apex_z:.6g} {WIRE_RADIUS_M:.6g}",
        f"GW 2 {_segments(max(FEED_Z - RH, 0.1), lam)} 0 0 {FEED_Z:.6g} 0 0 {RH:.6g} {WIRE_RADIUS_M:.6g}",
        f"GW 3 {_segments(ret_m, lam)} 0 0 {RH:.6g} {-ret_m:.6g} 0 {RH:.6g} {WIRE_RADIUS_M:.6g}",
    ]
    return (
        "\n".join(
            [
                "CM sloper",
                "CE",
                *w,
                "GE 1",
                f"GN 2 0 0 0 {eps:g} {sig:g}",
                "EX 0 1 1 0 1.0 0.0",
                f"FR 0 1 0 0 {freq / 1e6:g} 0",
                "XQ",
                "EN",
            ]
        )
        + "\n"
    )


print(f"Sloper fed at {FEED_Z:g} m, rising to an apex, against the flat model.")
print("|Z| ratio, sloper over flat.  x1.00 would mean the assumption holds.\n")
print(
    f"{'MHz':>7} {'apex m':>7} {'vs flat at apex':>22} {'vs flat at mean height':>24}"
)
for freq in (7.15e6, 14.175e6):
    lam = C / freq
    with tempfile.TemporaryDirectory() as w:
        for apex in (10.0, 20.0):
            mean_h = (FEED_Z + apex) / 2
            ra, rm = [], []
            for ratio in RATIOS:
                L = ratio * lam
                d = sloper_deck(L, freq, apex, RETURN_M)
                if d is None:
                    continue
                zs = run(d, w)
                za = run(end_fed_deck(L, freq, apex, RETURN_M, ground=SOIL), w)
                zm = run(end_fed_deck(L, freq, mean_h, RETURN_M, ground=SOIL), w)
                if np.isfinite(zs.real):
                    ra.append(abs(zs) / abs(za))
                    rm.append(abs(zs) / abs(zm))
            f = lambda v: (
                f"med x{np.exp(np.median(np.abs(np.log(v)))):.2f} worst x{np.exp(np.abs(np.log(v)).max()):.2f}"
            )
            print(f"{freq / 1e6:7.3f} {apex:7.1f} {f(ra):>22} {f(rm):>24}")
