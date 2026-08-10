"""Ground behaviour at low height, done as a curve rather than a minimum.

Forcing a single minimum was the wrong instrument: at h = 5 m with a short
return there is no clean low-Z resonance to find, and the search ran into
its own scan boundary.  Print the whole |Z| curve per ground instead.  If
the curves are the same shape displaced in length, it is a resonance shift;
if they share a shape and differ in amplitude, it is loss.
"""

import numpy as np

from nec_model import C, GROUNDS, end_fed_zin

FREQ_HZ = 14.2e6
HEIGHTS_M = (3.0, 5.0, 10.0)
RETURN_M = 5.0

if __name__ == "__main__":
    lam = C / FREQ_HZ
    ratios = np.arange(0.05, 0.65, 0.025)
    for h in HEIGHTS_M:
        print(f"\n=== h = {h} m, return {RETURN_M} m, f = {FREQ_HZ / 1e6} MHz ===")
        print(f"{'l/lambda':>9} " + "".join(f"{g:>12}" for g in GROUNDS))
        for r in ratios:
            row = [
                abs(end_fed_zin(r * lam, FREQ_HZ, h, RETURN_M, ground=g))
                for g in GROUNDS
            ]
            marks = "   <- peak spread" if max(row) / min(row) > 2.0 else ""
            print(f"{r:9.3f} " + "".join(f"{v:12.0f}" for v in row) + marks)
