"""Chase two anomalies from the probe.

A. Why does NEC read 133-3500 ohm at a "quarter wave" where the page model
   reads 52?  Decompose by replacing one unknown at a time: bond the return
   to a perfect ground, then degrade the ground, then free the return.

B. Is the ground ordering at low height really non-monotonic, or is it a
   resonance shift?  If it is a shift, the length of minimum |Z| moves with
   ground type; if it is loss, the length stays put and only |Z| changes.
   Low heights matter: improvised wires get hung low.
"""

import numpy as np
from PyNEC import nec_context

from nec_model import (
    C,
    GROUNDS,
    SEGMENTS_PER_WAVELENGTH,
    WIRE_RADIUS_M,
    end_fed_zin,
)

FREQ_HZ = 14.2e6


def _segs(length_m, wavelength_m):
    n = max(int(np.ceil(SEGMENTS_PER_WAVELENGTH * length_m / wavelength_m)), 9)
    return n + 1 if n % 2 == 0 else n


def inverted_l_zin(
    horizontal_m, height_m, freq_hz, ground=None, radius_m=WIRE_RADIUS_M
):
    """Inverted L: vertical drop bonded to ground, horizontal top wire.

    ground=None means a perfectly conducting plane.  This is the geometry the
    textbook quarter-wave figure actually describes once the feed has a real
    return: the radiator is drop + top, not the top alone.
    """
    wavelength_m = C / freq_hz
    ctx = nec_context()
    geo = ctx.get_geometry()
    # Vertical, bonded at z = 0, fed at its base segment.
    geo.wire(1, _segs(height_m, wavelength_m), 0, 0, 0, 0, 0, height_m, radius_m, 1, 1)
    if horizontal_m > 0:
        geo.wire(
            2,
            _segs(horizontal_m, wavelength_m),
            0,
            0,
            height_m,
            horizontal_m,
            0,
            height_m,
            radius_m,
            1,
            1,
        )
    ctx.geometry_complete(1)
    if ground is None:
        ctx.gn_card(1, 0, 0, 0, 0, 0, 0, 0)
    else:
        eps, sigma = GROUNDS[ground]
        ctx.gn_card(2, 0, eps, sigma, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


def min_z_length(height_m, return_m, ground, ratios, freq_hz=FREQ_HZ):
    """Antenna length near a quarter wave giving the smallest |Z|."""
    lam = C / freq_hz
    best = min(
        ratios,
        key=lambda r: abs(
            end_fed_zin(r * lam, freq_hz, height_m, return_m, ground=ground)
        ),
    )
    return best, end_fed_zin(best * lam, freq_hz, height_m, return_m, ground=ground)


if __name__ == "__main__":
    lam = C / FREQ_HZ
    quarter = lam / 4
    print(f"lambda = {lam:.2f} m, quarter wave = {quarter:.2f} m\n")

    print("=== A. decomposing the quarter-wave gap ===")
    print("page model at its own quarter wave:            52.1 ohm\n")
    print("A1  vertical lam/4, perfect ground, bonded")
    print(f"      {inverted_l_zin(0.0, quarter, FREQ_HZ):.1f}")
    # A2 and A3 hold drop + top at a quarter wave, so the drop cannot exceed
    # one.  A taller drop would leave a negative top wire, which builds a bare
    # vertical instead and quietly answers a different question.
    inverted_heights = tuple(h for h in (1.0, 2.0, 4.0, 5.0) if h < quarter)
    print("A2  inverted L, drop + top = lam/4, perfect ground, bonded")
    for h in inverted_heights:
        z = inverted_l_zin(quarter - h, h, FREQ_HZ)
        print(f"      h={h:4.1f} top={quarter - h:5.2f}  {z:>16.1f}")
    print("A3  same, average ground (adds ground loss only)")
    for h in inverted_heights:
        z = inverted_l_zin(quarter - h, h, FREQ_HZ, ground="average")
        print(f"      h={h:4.1f} top={quarter - h:5.2f}  {z:>16.1f}")
    print("A4  top wire alone = lam/4 (what the page calls a quarter wave),")
    print("    bonded drop, average ground -- return no longer counted in l")
    for h in (2.0, 5.0, 10.0):
        z = inverted_l_zin(quarter, h, FREQ_HZ, ground="average")
        print(f"      h={h:4.1f} total={quarter + h:5.2f}  {z:>16.1f}")
    print("A5  unbonded return, our sweep geometry, h=10")
    for ret in (5.0, 15.0, 30.0):
        z = end_fed_zin(quarter, FREQ_HZ, 10.0, ret)
        print(f"      ret={ret:4.1f}          {z:>16.1f}")

    print("\n=== B. ground ordering at low height ===")
    print("h = 5 m, return 5 m; scanning antenna length for minimum |Z|.")
    ratios = np.arange(0.15, 0.42, 0.005)
    print(f"{'ground':>8} {'best l/lambda':>14} {'|Z| there':>11} {'|Z| at 0.25':>12}")
    for g in GROUNDS:
        r, z = min_z_length(5.0, 5.0, g, ratios)
        z25 = end_fed_zin(0.25 * lam, FREQ_HZ, 5.0, 5.0, ground=g)
        print(f"{g:>8} {r:14.3f} {abs(z):11.1f} {abs(z25):12.1f}")
    print("resonance moving with ground => shift; staying put => loss.")
