"""How much do the return path's unswept geometry choices matter?

The sweep fixed two things about the return that real installations vary:
which way it runs from the feedpoint, and how high off the ground it lies.
Neither was ever tested, and both are choices rather than measurements.

Bearing is the mild one.  A counterpoise wire is often laid out along the
antenna, while a feedline acting as counterpoise usually heads away, at
anything from in line to 45 degrees off to square.  All of it is real.

Height is the sharp one, and the sweep's 5 cm stands for a feedline or
counterpoise lying on the soil.  Elevated returns are a different antenna.
"""

import numpy as np
from PyNEC import nec_context

from nec_model import C, GROUNDS, RETURN_HEIGHT_M, WIRE_RADIUS_M, _segments

FT = 0.3048

#: The page's default site.
HEIGHT_M = 9.144
RETURN_M = 7.62
SOIL = "average"
UNUN = 9.0

BANDS = {
    "80m": 3.75e6,
    "40m": 7.15e6,
    "20m": 14.175e6,
    "15m": 21.225e6,
    "10m": 28.85e6,
}

BEARINGS_DEG = (0, 45, 90, 135, 180)
RETURN_HEIGHTS_M = (0.01, 0.05, 0.25, 1.0, 2.0)
LENGTHS_FT = (71.0, 84.0)


def zin(length_m, freq_hz, return_height_m, bearing_deg, radius_m=WIRE_RADIUS_M):
    """Feedpoint Z with the return at a given bearing and height."""
    wavelength_m = C / freq_hz
    ctx = nec_context()
    geo = ctx.get_geometry()
    geo.wire(
        1,
        _segments(length_m, wavelength_m),
        0,
        0,
        HEIGHT_M,
        length_m,
        0,
        HEIGHT_M,
        radius_m,
        1,
        1,
    )
    geo.wire(
        2,
        _segments(HEIGHT_M, wavelength_m),
        0,
        0,
        HEIGHT_M,
        0,
        0,
        return_height_m,
        radius_m,
        1,
        1,
    )
    theta = np.radians(bearing_deg)
    geo.wire(
        3,
        _segments(RETURN_M, wavelength_m),
        0,
        0,
        return_height_m,
        RETURN_M * np.cos(theta),
        RETURN_M * np.sin(theta),
        return_height_m,
        radius_m,
        1,
        1,
    )
    ctx.geometry_complete(1)
    eps, sigma = GROUNDS[SOIL]
    ctx.gn_card(2, 0, eps, sigma, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, freq_hz / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


def swr(z, ratio=UNUN):
    g = abs((z / ratio - 50.0) / (z / ratio + 50.0))
    return (1 + g) / (1 - g)


def table(length_ft, values, vary_height):
    """One sensitivity table: SWR per band against the varied quantity."""
    print(
        f"=== {length_ft:g} ft, "
        f"{'return height (m)' if vary_height else 'return bearing (deg)'} ==="
    )
    print(f"{'band':>5} " + " ".join(f"{v:>7}" for v in values) + f" {'spread':>8}")
    for name, freq in BANDS.items():
        row = [
            swr(
                zin(
                    length_ft * FT,
                    freq,
                    v if vary_height else RETURN_HEIGHT_M,
                    0 if vary_height else v,
                )
            )
            for v in values
        ]
        print(
            f"{name:>5} "
            + " ".join(f"{x:7.1f}" for x in row)
            + f" {max(row) / min(row):7.2f}x"
        )
    print()


if __name__ == "__main__":
    print("Bearing: 0 is in line under the antenna, 180 straight away.\n")
    for length_ft in LENGTHS_FT:
        table(length_ft, BEARINGS_DEG, vary_height=False)

    print(
        f"Height: every shipped number used {RETURN_HEIGHT_M} m; "
        "0.01 approximates lying on the soil.\n"
    )
    for length_ft in LENGTHS_FT:
        table(length_ft, RETURN_HEIGHTS_M, vary_height=True)
