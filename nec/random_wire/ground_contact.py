"""What does holding the return 5 cm off the soil actually cost?

`nec_model.RETURN_HEIGHT_M` is 0.05 m, and the reason is a NEC-2 limit
rather than a modelling choice: a wire bonded to the ground plane shorts
the source, so the return has to float just above it.  Most people simply
let the coax lie on the dirt, so the standoff is an approximation nobody
asked for.

NEC-4 can put wires at and below the interface, so the assumption can be
tested rather than carried.  Three things have to be right:

  - the vertical drop must be split at z = 0.  NEC will not accept a
    segment spanning the interface, and the error names the drop rather
    than the return: "SEGMENT n EXTENDS BELOW GROUND".
  - `GE 0` or `GE -1`, not `GE 1`.  `GE 1` bonds wires touching the
    ground plane and rejects anything at or below it.  All three agree
    exactly for a return above ground, so the flag is not changing the
    ground itself.
  - z = 0 exactly is degenerate and must be avoided.  It returns a value
    inconsistent with both sides -- 281 ohms where 1 cm above gives 2585
    and 1 cm below gives 2123 -- because the wire then lies in the
    interface.  A depth of a millimetre fails outright in junction
    finding.

The finding: it depends entirely on where the antenna is electrically.
Near half- and full-wave multiples, where |Zin| is high and the antenna
wire dominates, burying the return moves the answer by about 15 percent.
At a quarter wave, where |Zin| is low and the return path dominates, it
moves it by up to a factor of 5.  That is the regime the length picker
works in, so the standoff is not a harmless artifact.

Neither position is the real one.  Coax lying on soil sits with its axis
about one radius above the surface, seeing air above and soil below;
5 cm up is all air and 5 cm down is all soil, and they bracket the truth
rather than bounding it tightly.  What this script establishes is the
size of that bracket, not which end to believe.

    uv run python ground_contact.py /usr/bin/nec4d42
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from nec_model import C, GROUNDS, WIRE_RADIUS_M, _segments

#: Depths and heights to walk through the interface.  0.0 and -0.001 are
#: omitted deliberately; see the module docstring.
RETURN_HEIGHTS_M = (0.5, 0.1, 0.05, 0.01, -0.01, -0.05, -0.1, -0.5)

#: The pair the comparison turns on: the shipped standoff, and its mirror
#: image just under the surface.
ABOVE_M, BELOW_M = 0.05, -0.05

FREQS_HZ = (1.9e6, 7.15e6, 14.175e6, 28.85e6)
HEIGHTS_M = (3.0, 10.0, 20.0)
RETURN_M = 7.62

#: A quarter wave is the low-impedance case where the return dominates;
#: the half and full wave are the high-impedance cases where it does not.
RATIOS = (0.25, 0.5, 1.0)

SOIL = "average"
IMPEDANCE_FIELD = 4
SCIENTIFIC = re.compile(r"[-+]?\d*\.?\d+[Ee][-+]?\d+")


def deck(length_m, freq_hz, height_m, return_len_m, return_height_m):
    """The page's geometry, with the return free to sit below ground.

    Above the interface this is `nec_model.end_fed_deck`.  Below it the
    drop becomes two wires meeting at z = 0, since a segment may not span
    the interface, and `GE 0` replaces `GE 1` so that wires reaching the
    surface are not bonded to it.
    """
    wavelength_m = C / freq_hz
    eps, sigma = GROUNDS[SOIL]
    wires = [
        f"GW 1 {_segments(length_m, wavelength_m)} 0 0 {height_m:.9g} "
        f"{length_m:.9g} 0 {height_m:.9g} {WIRE_RADIUS_M:.9g}"
    ]
    if return_height_m >= 0:
        wires.append(
            f"GW 2 {_segments(height_m - return_height_m, wavelength_m)} "
            f"0 0 {height_m:.9g} 0 0 {return_height_m:.9g} {WIRE_RADIUS_M:.9g}"
        )
    else:
        wires.append(
            f"GW 2 {_segments(height_m, wavelength_m)} 0 0 {height_m:.9g} "
            f"0 0 0 {WIRE_RADIUS_M:.9g}"
        )
        wires.append(
            f"GW 4 {max(3, _segments(abs(return_height_m), wavelength_m))} "
            f"0 0 0 0 0 {return_height_m:.9g} {WIRE_RADIUS_M:.9g}"
        )
    wires.append(
        f"GW 3 {_segments(return_len_m, wavelength_m)} 0 0 "
        f"{return_height_m:.9g} {return_len_m:.9g} 0 {return_height_m:.9g} "
        f"{WIRE_RADIUS_M:.9g}"
    )
    return (
        "\n".join(
            [
                "CM end-fed wire, return free to cross the interface",
                "CE",
                *wires,
                "GE 0",
                f"GN 2 0 0 0 {eps:.9g} {sigma:.9g}",
                "EX 0 1 1 0 1.0 0.0",
                f"FR 0 1 0 0 {freq_hz / 1e6:.9g} 0",
                "XQ",
                "EN",
            ]
        )
        + "\n"
    )


def parse_impedance(text):
    """Pull the source impedance out of an ANTENNA INPUT PARAMETERS table."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "(WATTS)" not in line:
            continue
        for row in lines[i + 1 :]:
            values = SCIENTIFIC.findall(row)
            if len(values) >= IMPEDANCE_FIELD + 2:
                real, imag = values[IMPEDANCE_FIELD : IMPEDANCE_FIELD + 2]
                return complex(float(real), float(imag))
    return None


def solve(binary, work, deck_text):
    """One NEC-4 solve.  None if it refused the geometry."""
    source = Path(work) / "in.nec"
    result = Path(work) / "out.txt"
    source.write_text(deck_text)
    done = subprocess.run(
        [binary, str(source), str(result)], capture_output=True, cwd=work
    )
    if done.returncode != 0 or not result.exists():
        return None
    return parse_impedance(result.read_text())


def walk_the_interface(binary, work):
    """One geometry, taken down through the surface and under it."""
    print("A 107 ft wire 30 ft up, 25 ft return, 7.15 MHz, average soil.\n")
    print(f"{'return z (m)':>13} {'|Z| ohms':>10}")
    for return_height_m in RETURN_HEIGHTS_M:
        z = solve(binary, work, deck(32.6136, 7.15e6, 9.144, RETURN_M, return_height_m))
        print(
            f"{return_height_m:13g} {abs(z):10.1f}"
            if z
            else f"{return_height_m:13g} {'refused':>10}"
        )


def bracket(binary):
    """The standoff against its mirror image, across the grid."""
    print(f"\n\n{ABOVE_M:g} m above the soil against {abs(BELOW_M):g} m below it.\n")
    print(f"{'MHz':>7} {'h m':>5} {'l/lam':>6} {'above':>9} {'below':>9} {'ratio':>7}")
    worst, worst_low = 1.0, 1.0
    for freq_hz in FREQS_HZ:
        wavelength_m = C / freq_hz
        # A directory per frequency.  NEC-4 caches its Sommerfeld grid in
        # SOMD.NEC in the working directory, and that grid is a function of
        # frequency, so sharing one across frequencies would risk reusing a
        # stale one.  Sharing within a frequency is safe: the soil is fixed.
        with tempfile.TemporaryDirectory(prefix="gc-") as work:
            for height_m in HEIGHTS_M:
                for ratio in RATIOS:
                    length_m = ratio * wavelength_m
                    args = (length_m, freq_hz, height_m, RETURN_M)
                    above = solve(binary, work, deck(*args, ABOVE_M))
                    below = solve(binary, work, deck(*args, BELOW_M))
                    if not (above and below):
                        continue
                    factor = abs(below) / abs(above)
                    worst = max(worst, factor, 1 / factor)
                    if ratio == 0.25:
                        worst_low = max(worst_low, factor, 1 / factor)
                    print(
                        f"{freq_hz / 1e6:7.3f} {height_m:5g} {ratio:6.2f} "
                        f"{abs(above):9.1f} {abs(below):9.1f} {factor:7.3f}"
                    )
    print(f"\nworst overall x{worst:.2f}, worst at a quarter wave x{worst_low:.2f}")
    print(
        "The quarter wave is where the return path dominates the feedpoint,\n"
        "and it is where the length picker operates.  The standoff is a\n"
        "modelling assumption with teeth, not a harmless artifact."
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: ground_contact.py /path/to/nec4d42")
    with tempfile.TemporaryDirectory(prefix="gc-") as work:
        walk_the_interface(sys.argv[1], work)
    bracket(sys.argv[1])
