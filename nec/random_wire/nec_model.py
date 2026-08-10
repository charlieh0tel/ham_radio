"""NEC geometry for an end-fed wire with an explicit return path.

Scratch instrument, not shipped: PyNEC is GPL and the ham_radio repo is
MIT.  Only fitted numbers cross back over, which a program's output
licence does not cover.

Geometry, matching how a random wire is actually hung:

    feedpoint ---------------------------- far end (open)   height h
        |
        | vertical drop, length h
        |
        +========== feedline / counterpoise ========== station   ground

The antenna wire runs horizontally at height h.  The return path leaves
the feedpoint, drops to just above ground, and runs horizontally for
`return_len_m`.  That single wire stands for either real case: the coax
shield carrying common-mode current back to the station, or a
counterpoise wire thrown out along the ground.
"""

import numpy as np
from PyNEC import nec_context

C = 299792458.0

#: #14 AWG, the page's default conductor.
WIRE_RADIUS_M = 1.628e-3 / 2

#: Ground constants (permittivity, conductivity S/m).  The three standard
#: NEC cases; values from the ARRL Antenna Book's ground conductivity table.
GROUNDS = {
    "poor": (5.0, 0.001),  # rocky, sandy, mountainous
    "average": (13.0, 0.005),  # medium soil, the usual default
    "good": (20.0, 0.030),  # rich damp soil, marshy
}

#: NEC wants segments short against a wavelength; 20 per wavelength is the
#: usual accuracy rule, and short against the radius is automatic here.
SEGMENTS_PER_WAVELENGTH = 20
MIN_SEGMENTS = 9

#: How high the return path lies, metres.  Not at z = 0 because bonding it to
#: ground would short the source.
#:
#: This stands for a feedline or counterpoise lying on the soil, which is the
#: common case, and 0.01 m gives nearly the same answer, so the choice is safe
#: for that install.  It is not a small assumption in general: per
#: geometry_check.py, raising the return to 1-2 m moves the feedpoint by up to
#: 4.6x on 20 m, far outside the quoted bound.  An elevated counterpoise or a
#: feedline on standoffs is a different antenna and this model does not cover
#: it.
RETURN_HEIGHT_M = 0.05

#: Which way the return runs from the feedpoint, along the antenna (+1) or
#: away from it (-1).
#:
#: Both are real.  A counterpoise wire often gets laid out along the antenna,
#: while a feedline acting as counterpoise usually heads away, at anything
#: from in line to square.  geometry_check.py measures what the choice is
#: worth and the answer is little: 1.20x on 80 m and 1.07x or less elsewhere,
#: because the return lies close to lossy ground whose image largely cancels
#: its coupling to the elevated wire.
RETURN_DIRECTION = 1


def _segments(length_m, wavelength_m):
    """Segment count for a wire, odd so a centre segment exists."""
    n = int(np.ceil(SEGMENTS_PER_WAVELENGTH * length_m / wavelength_m))
    n = max(n, MIN_SEGMENTS)
    return n + 1 if n % 2 == 0 else n


def end_fed_zin(
    length_m,
    freq_hz,
    height_m,
    return_len_m,
    ground="average",
    radius_m=WIRE_RADIUS_M,
):
    """Feedpoint impedance of a horizontal end-fed wire over ground.

    The source sits on the first segment of the antenna wire, at the
    junction with the return path, which is where a real unun goes.
    """
    wavelength_m = C / freq_hz
    ctx = nec_context()
    geo = ctx.get_geometry()

    # Tag 1: the antenna wire, running out from the feedpoint at height h.
    geo.wire(
        1,
        _segments(length_m, wavelength_m),
        0.0,
        0.0,
        height_m,
        length_m,
        0.0,
        height_m,
        radius_m,
        1,
        1,
    )
    # Tag 2: the vertical drop from the feedpoint down toward ground.
    geo.wire(
        2,
        _segments(height_m, wavelength_m),
        0.0,
        0.0,
        height_m,
        0.0,
        0.0,
        RETURN_HEIGHT_M,
        radius_m,
        1,
        1,
    )
    # Tag 3: the return run.  RETURN_DIRECTION decides whether it lies under
    # the antenna or heads away from it; see the constant.
    geo.wire(
        3,
        _segments(return_len_m, wavelength_m),
        0.0,
        0.0,
        RETURN_HEIGHT_M,
        RETURN_DIRECTION * return_len_m,
        0.0,
        RETURN_HEIGHT_M,
        radius_m,
        1,
        1,
    )

    ctx.geometry_complete(1)
    eps, sigma = GROUNDS[ground]
    # Ground type 2 is the Sommerfeld-Norton solution, the accurate one for
    # wires close to a lossy earth.
    ctx.gn_card(2, 0, eps, sigma, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]
