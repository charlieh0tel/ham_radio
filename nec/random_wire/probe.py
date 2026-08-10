"""Decide-first probe: how far is the shipped model off, and does height matter?

Compares NEC against the page's current coth model at the two anchors, over
the height and return-length spread a real installation covers.
"""

import numpy as np

from nec_model import C, GROUNDS, WIRE_RADIUS_M, end_fed_zin

HALF_WAVE_OHMS = 2450.0  # the page's anchor
UNUN_RATIO = 9.0
Z_SYSTEM = 50.0

FREQ_HZ = 14.2e6
HEIGHTS_M = (5.0, 10.0, 20.0)
RETURNS_M = (5.0, 15.0, 30.0)


def page_zin(length_m, freq_hz, velocity_factor=0.95, radius_m=WIRE_RADIUS_M):
    """The model random-wire.html ships today: Zin = Z0 coth(gamma l)."""
    z0 = 60.0 * (np.log(2.0 * length_m / radius_m) - 1.0)
    wavelength_m = (C / freq_hz) * velocity_factor
    quarter_ohms = z0 * z0 / (2.0 * HALF_WAVE_OHMS)
    alpha = np.arctanh(quarter_ohms / z0) / (wavelength_m / 4.0)
    beta = 2.0 * np.pi / wavelength_m
    return z0 / np.tanh(complex(alpha * length_m, beta * length_m))


def swr(z, ratio=UNUN_RATIO):
    g = abs((z / ratio - Z_SYSTEM) / (z / ratio + Z_SYSTEM))
    return (1 + g) / (1 - g) if g < 1 else np.inf


if __name__ == "__main__":
    lam = C / FREQ_HZ
    for name, ratio in (("quarter wave", 0.25), ("half wave", 0.5)):
        length = ratio * lam
        print(f"\n=== {name}, l = {length:.2f} m, f = {FREQ_HZ / 1e6} MHz ===")
        print(
            f"page model: {page_zin(length, FREQ_HZ):>18.1f}"
            f"   SWR {swr(page_zin(length, FREQ_HZ)):6.2f}"
        )
        print(
            f"{'h (m)':>6} {'ret (m)':>8} {'ground':>8} "
            f"{'NEC Zin':>20} {'|Z|':>9} {'SWR/9:1':>8}"
        )
        for h in HEIGHTS_M:
            for r in RETURNS_M:
                for g in GROUNDS:
                    z = end_fed_zin(length, FREQ_HZ, h, r, ground=g)
                    print(
                        f"{h:6.0f} {r:8.0f} {g:>8} "
                        f"{z:>20.1f} {abs(z):9.1f} {swr(z):8.2f}"
                    )
