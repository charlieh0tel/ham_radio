"""Reproducer: nec2c's Sommerfeld ground is wrong close to the interface.

For https://github.com/charlieh0tel/nec2c-js -- run this, then run the
JavaScript half in the docstring below, and compare.

## What is wrong

nec2c and nec2++ are independent translations of the same NEC-2 FORTRAN.
Over a real ground they disagree by up to a factor of two when a wire sits
within about 0.01 wavelengths of the interface.  Two tests place the fault
in nec2c rather than in either implementation's geometry handling.

**Perfect ground.**  Replace the soil with a perfect conductor, which is
image theory and involves no Sommerfeld integral.  The two agree to 0.01
percent at exactly the heights where they were 40 to 98 percent apart
with real soil.  So the geometry, the segmentation and the near-field
handling are sound in both.

**The conductivity limit, which decides it.**  As a soil's conductivity
rises it becomes a perfect ground plane, so `GN 2` must converge to the
`GN 1` answer.  That answer is known and both compute it identically.
nec2++ converges to it within 0.03 percent.  nec2c stops about 30 percent
above it and stays there.

A limit with a known answer that an implementation does not reach is a
bug, not a defensible reading of a hard integral.  The Sommerfeld-Norton
ground is documented as accurate for wires as close to it as to a perfect
ground, so this is not the method being used outside its envelope.

## Why it matters here

`docs/random-wire.html` models a feedline lying on the soil, 5 cm up.
That is the regime where nec2c is 30 percent high, so an in-browser check
built on it would contradict the page's own coefficients -- which are
fitted against nec2++ -- for reasons invisible to the user.

## The JavaScript half

    import { buildDeck, parseOutput } from 'nec2c-deck';
    import { runNec } from 'nec2c-wasm';

    const C = 299792458, R = 8.14e-4, FT = 0.3048;
    const f = 7.15e6, lam = C / f;
    const L = 107 * FT, h = 30 * FT, ret = 25 * FT, rh = 0.05;
    const seg = (l) => {
      const n = Math.max(Math.ceil(20 * l / lam), 9);
      return n % 2 === 0 ? n + 1 : n;
    };
    const wires = [
      { tag: 1, segments: seg(L),      x1: 0, y1: 0, z1: h,
        x2: L, y2: 0, z2: h,   radiusM: R },
      { tag: 2, segments: seg(h - rh), x1: 0, y1: 0, z1: h,
        x2: 0, y2: 0, z2: rh,  radiusM: R },
      { tag: 3, segments: seg(ret),    x1: 0, y1: 0, z1: rh,
        x2: ret, y2: 0, z2: rh, radiusM: R },
    ];
    const src = [{ tag: 1, segment: 1, vReal: 1, vImag: 0 }];
    const grid = { ntheta: 1, nphi: 1, theta0: 0, phi0: 0, dtheta: 0, dphi: 0 };

    for (const sigma of [0.03, 1, 30, 1000]) {
      const deck = buildDeck(['limit'], wires, src,
        { epsR: 20, sigmaSm: sigma }, f / 1e6, grid);
      const s = parseOutput(await runNec(deck)).sources[0];
      console.log(sigma, Math.hypot(s.zReal, s.zImag).toFixed(1));
    }
    // and once more with `true` in place of the ground object, for GN 1.
"""

from PyNEC import nec_context

from nec_model import C, WIRE_RADIUS_M, _segments

FT = 0.3048

#: One geometry, the one the page assumes: a 107 ft wire 30 ft up, fed at
#: the end, with a 25 ft return lying 5 cm off the soil.
FREQ_HZ = 7.15e6
LENGTH_M = 107 * FT
HEIGHT_M = 30 * FT
RETURN_M = 25 * FT
RETURN_HEIGHT_M = 0.05

#: Rising conductivity, ending far enough up that the soil is effectively a
#: conductor and the answer must equal the perfect-ground one.
SIGMAS_S_PER_M = (0.03, 1.0, 30.0, 1000.0)
EPS_R = 20.0


def zin(sigma_s_per_m=None, return_height_m=RETURN_HEIGHT_M):
    """Feedpoint Z.  sigma_s_per_m None means a perfect ground plane."""
    wavelength_m = C / FREQ_HZ
    ctx = nec_context()
    geo = ctx.get_geometry()
    geo.wire(
        1,
        _segments(LENGTH_M, wavelength_m),
        0,
        0,
        HEIGHT_M,
        LENGTH_M,
        0,
        HEIGHT_M,
        WIRE_RADIUS_M,
        1,
        1,
    )
    geo.wire(
        2,
        _segments(HEIGHT_M - return_height_m, wavelength_m),
        0,
        0,
        HEIGHT_M,
        0,
        0,
        return_height_m,
        WIRE_RADIUS_M,
        1,
        1,
    )
    geo.wire(
        3,
        _segments(RETURN_M, wavelength_m),
        0,
        0,
        return_height_m,
        RETURN_M,
        0,
        return_height_m,
        WIRE_RADIUS_M,
        1,
        1,
    )
    ctx.geometry_complete(1)
    if sigma_s_per_m is None:
        ctx.gn_card(1, 0, 0, 0, 0, 0, 0, 0)
    else:
        ctx.gn_card(2, 0, EPS_R, sigma_s_per_m, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, FREQ_HZ / 1e6, 0)
    ctx.xq_card(0)
    return abs(ctx.get_input_parameters(0).get_impedance()[0])


if __name__ == "__main__":
    perfect = zin(None)
    print("nec2++ (PyNEC), 107 ft wire 30 ft up, 25 ft return 5 cm off soil,")
    print(f"7.15 MHz, eps_r {EPS_R:g}\n")
    print(f"{'sigma S/m':>10} {'|Z| ohms':>10} {'vs perfect':>11}")
    for sigma in SIGMAS_S_PER_M:
        value = zin(sigma)
        print(f"{sigma:10g} {value:10.1f} {100 * (value / perfect - 1):+10.1f}%")
    print(f"{'perfect':>10} {perfect:10.1f} {0.0:+10.1f}%")
    print("\nExpected: the last GN 2 row converges on the perfect-ground row.")
    print("nec2++ reaches it within 0.03 percent.  nec2c stops about 30")
    print("percent above and does not move with further conductivity.")

    print("\nSame check with the return lifted clear of the interface,")
    print("where the two implementations already agree:")
    print(f"{'return h m':>11} {'|Z| ohms':>10}")
    for return_height_m in (0.05, 0.5, 2.0):
        print(f"{return_height_m:11g} {zin(0.03, return_height_m):10.1f}")
