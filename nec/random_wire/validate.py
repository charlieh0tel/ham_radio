"""Sanity checks before trusting any sweep output.

Two textbook cases pin the driver itself, then the end-fed geometry is
exercised over the quarter/half wave pattern it exists to capture.
"""

from PyNEC import nec_context

from nec_model import C, WIRE_RADIUS_M, end_fed_zin

SEGMENTS = 101


def monopole_zin(length_m, freq_hz, radius_m=WIRE_RADIUS_M, segments=SEGMENTS):
    """Base-fed vertical monopole over perfect ground.  Expect ~36 + j21."""
    ctx = nec_context()
    geo = ctx.get_geometry()
    # The lower end must sit exactly at z = 0 to bond to the ground plane.
    geo.wire(1, segments, 0, 0, 0, 0, 0, length_m, radius_m, 1, 1)
    ctx.geometry_complete(1)
    ctx.gn_card(1, 0, 0, 0, 0, 0, 0, 0)  # perfectly conducting ground
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


def dipole_zin(length_m, freq_hz, radius_m=WIRE_RADIUS_M, segments=SEGMENTS):
    """Centre-fed dipole in free space.  Expect ~73 + j42."""
    ctx = nec_context()
    geo = ctx.get_geometry()
    geo.wire(1, segments, 0, 0, -length_m / 2, 0, 0, length_m / 2, radius_m, 1, 1)
    ctx.geometry_complete(0)
    ctx.ex_card(0, 1, segments // 2 + 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


if __name__ == "__main__":
    freq = 14.2e6
    lam = C / freq
    print(f"f = {freq / 1e6} MHz, lambda = {lam:.3f} m\n")

    print("-- driver against textbook cases --")
    print(f"quarter-wave monopole, perfect gnd: {monopole_zin(lam / 4, freq):.1f}")
    print("                                    expect ~36+j21")
    print(f"half-wave dipole, free space:       {dipole_zin(lam / 2, freq):.1f}")
    print("                                    expect ~73+j42")

    print("\n-- end-fed geometry, h = 10 m, 15 m return, average ground --")
    for ratio in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
        z = end_fed_zin(ratio * lam, freq, 10.0, 15.0)
        print(f"  l = {ratio:4.2f} lambda: {z:>18.1f}   |Z| = {abs(z):8.1f}")
    print("  expect low Z at odd quarter waves, kilohms at half-wave multiples")
