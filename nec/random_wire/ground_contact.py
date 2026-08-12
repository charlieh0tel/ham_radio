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

## The case we actually want is the one NEC cannot express

Neither position is the real one, and tightening the bracket does not
help: closing it from 5 cm to 1 cm either side leaves it no tighter and
makes it worse at a quarter wave, x2.19 median against x1.57.  The two
limits do not converge on contact.

They cannot.  The thin-wire kernel assumes a homogeneous medium around
the conductor.  A wire lying on the surface has half its near field in
air and half in soil, which is neither branch: from above the wire is
entirely in air, from below entirely in soil.  Hence z = 0 returning a
value consistent with neither.  The above branch also runs out before
contact -- at 1 mm our #14 wire is 1.2 radii up, its surface 0.19 mm
from the soil, and the answer breaks an otherwise monotonic trend -- so
it is usable to about 1 cm and no further.

Insulation does not rescue this.  A jacket is a few-percent effect, the
same one that gives insulated wire a velocity factor near 0.95 rather
than 1.0: it raises the effective radius and lightly loads the line.  It
does not move the conductor into the air regime, because soil at HF is a
lossy dielectric rather than a conductor -- loss tangent 3.6 at 1.9 MHz
falling to 0.24 at 28.85, skin depth metres throughout -- so a wire in
contact is not shorted to anything, and touching versus a millimetre off
is not the discontinuity a jacket would protect against.

So what justifies keeping the return above ground is mechanical, not
electrical: real ground is not flat.  Coax drapes over grass, leaf
litter and ruts, so a centimetre or two of average clearance describes
a real install.  Burial is the wrong model for something lying on top,
and the right one for radials under the turf, which is a different
installation.

    uv run python ground_contact.py /usr/bin/nec4d42
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from nec_model import C, GROUNDS, WIRE_RADIUS_M, _segments

#: Depths and heights to walk through the interface.  0.0 and -0.001 are
#: omitted deliberately; see the module docstring.
RETURN_HEIGHTS_M = (0.5, 0.1, 0.05, 0.01, -0.01, -0.05, -0.1, -0.5)

#: Brackets across the interface, each a height and its mirror image.  Two
#: of them, because the question is not only how wide the bracket is but
#: whether closing it converges on contact.  It does not.
BRACKETS = ((0.05, -0.05), (0.01, -0.01))

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


def bracket(binary, above_m, below_m):
    """One bracket across the interface, over the grid.  Returns the ratios."""
    ratios, quarter = [], []
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
                    above = solve(binary, work, deck(*args, above_m))
                    below = solve(binary, work, deck(*args, below_m))
                    if not (above and below):
                        continue
                    factor = abs(below) / abs(above)
                    ratios.append(factor)
                    if ratio == 0.25:
                        quarter.append(factor)
    return ratios, quarter


def report(label, ratios):
    """Spread of a bracket, geometrically: x2 and x0.5 are the same size."""
    if not ratios:
        print(f"{label:>10}  no points")
        return
    log = np.abs(np.log(ratios))
    print(
        f"{label:>10}  n={len(ratios):3d}  median x{np.exp(np.median(log)):.2f}  "
        f"90th x{np.exp(np.percentile(log, 90)):.2f}  "
        f"worst x{np.exp(log.max()):.2f}"
    )


def brackets(binary):
    """Both brackets, to show that closing one does not converge."""
    print("\n\nThe bracket across the interface, and whether closing it helps.\n")
    for above_m, below_m in BRACKETS:
        ratios, quarter = bracket(binary, above_m, below_m)
        print(f"+{above_m:g} m against {below_m:g} m")
        report("all", ratios)
        report("quarter", quarter)
        print()
    print(
        "Closing the bracket does not tighten it, and at a quarter wave it\n"
        "widens.  The two limits do not converge on contact, because a wire\n"
        "lying on the surface has half its near field in each medium and is\n"
        "neither of them.  The quarter wave is where the return dominates\n"
        "the feedpoint, and it is where the length picker operates."
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: ground_contact.py /path/to/nec4d42")
    with tempfile.TemporaryDirectory(prefix="gc-") as work:
        walk_the_interface(sys.argv[1], work)
    brackets(sys.argv[1])
