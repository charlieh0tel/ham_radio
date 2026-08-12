"""Conductivity-limit error against height, across NEC implementations.

`nec2c_ground_bug.py` asks whether an implementation can be trusted for
*this page's* installation, where the near-ground wire is the return and
the source is well up in the air.  This asks the more general question --
where does each implementation's Sommerfeld ground stop working -- by
putting the fed element itself near the soil and sweeping its height.

The test is the same and it is exact.  As conductivity rises a lossy
half-space becomes a perfect conductor, so `GN 2` at sigma 1e10 must
give what `GN 1` gives for the same geometry.  Every implementation
computes the `GN 1` side identically, so the gap is the error in the
Sommerfeld evaluation and nothing else.

The deck is a horizontal half-wave dipole, centre fed, from
nec2-js/investigations/sommerfeld_near_ground.nec.  The JavaScript
harness beside it, `sommerfeld.mjs`, runs one solver at a time and
carries the wasm build; this runs them side by side, which is what shows
that the disagreement is two-way rather than a spread.

Results are in docs/RANDOM_WIRE_MODEL.md, "Every implementation, against
height".  In short: all agree to 0.05 wavelengths, below which nec2++ and
PyNEC part company with the entire FORTRAN lineage -- nec2c both stock
and on its `validation` branch, nec2dx, and aegnec2 -- which agrees with
itself to three or four figures across five orders of magnitude of error.
Only nec2++ reaches the limit, and only down to about 0.005 wavelengths.

Usage, with any subset of the solvers:

    LD_LIBRARY_PATH=~/src/necpp/_install_/lib \\
    uv run python sommerfeld_cross.py \\
        nec2++=attached:~/src/necpp/_install_/bin/nec2++ \\
        nec2c=~/src/nec2c/nec2c \\
        nec2dx=attached:~/src/nec2c/nec2dx \\
        nec2dxs=stdio:~/src/nec2/nec2dxs \\
        aegnec2=jobname:~/src/aegnec2/_install_/bin/aegnec2

PyNEC is always included, in process.  `nec2dx` comes from nec2c's
`validation` branch; see nec2c_ground_bug.py for the build.

The runs build their decks in a temp directory and discard them.
`--decks=DIR` writes the same text out instead, two files per height, for
reproducing a row by hand or attaching to a bug report.  They are
generated rather than checked in, so the decks and the table cannot drift
apart.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PyNEC import nec_context

from nec_model import C

#: The deck, matching sommerfeld_near_ground.nec.  A half wave at this
#: frequency is 1.027 m, so a 1 m dipole is close to resonant.
FREQ_HZ = 145.9e6
HALF_LENGTH_M = 0.5
RADIUS_M = 0.001
SEGMENTS = 11
SOURCE_SEGMENT = 6

#: Permittivity is held fixed; at this conductivity it no longer matters.
EPS_R = 13.0
#: Far past any real material, standing in for the limit.
SIGMA_LIMIT_S_PER_M = 1e10

#: Heights in wavelengths.  Dense below 0.05, which is where the onset is.
HEIGHTS_WL = (0.5, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002)

#: Impedance is the third pair of numbers on the source row of the ANTENNA
#: INPUT PARAMETERS table: voltage, current, impedance, admittance.
IMPEDANCE_FIELD = 4

#: Fields there can abut with no separating space when a value is negative,
#: so split on the exponent form rather than on whitespace.
SCIENTIFIC = re.compile(r"[-+]?\d*\.?\d+[Ee][-+]?\d+")

#: How each implementation wants to be invoked, mapping a deck path and an
#: output path to the argv to use and where the report lands.  None means
#: the report comes back on stdout.  Names match sommerfeld.mjs.
STYLES = {
    "flags": lambda src, out: (["-i", str(src), "-o", str(out)], out),
    "attached": lambda src, out: ([f"-i{src}", f"-o{out}"], out),
    "stdio": lambda src, out: ([], None),
    "jobname": lambda src, out: ([str(src.with_suffix(""))], src.with_suffix(".res")),
}
DEFAULT_STYLE = "flags"


def deck(height_wl, sigma_s_per_m):
    """The dipole deck.  sigma_s_per_m None means GN 1, a perfect ground."""
    z = height_wl * C / FREQ_HZ
    if sigma_s_per_m is None:
        ground = "GN 1"
    else:
        ground = f"GN 2 0 0 0 {EPS_R:g} {sigma_s_per_m:g}"
    return (
        "\n".join(
            [
                f"CM sommerfeld probe h={height_wl}wl",
                "CE",
                f"GW 1 {SEGMENTS} {-HALF_LENGTH_M:g} 0 {z:.9g} "
                f"{HALF_LENGTH_M:g} 0 {z:.9g} {RADIUS_M:g}",
                "GE -1",
                ground,
                f"EX 0 1 {SOURCE_SEGMENT} 0 1.0 0.0",
                f"FR 0 1 0 0 {FREQ_HZ / 1e6:g} 0",
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
    raise ValueError("no impedance in solver output")


def run_deck(binary, text, style):
    """Solve a deck with an external NEC binary."""
    with tempfile.TemporaryDirectory(prefix="sc-") as work:
        source = Path(work) / "in.nec"
        source.write_text(text)
        args, out = STYLES[style](source, Path(work) / "out.txt")
        done = subprocess.run(
            [binary, *args],
            input=None if out else text.encode(),
            capture_output=True,
            check=True,
        )
        return parse_impedance(out.read_text() if out else done.stdout.decode())


def pynec(height_wl, sigma_s_per_m):
    """The same geometry through PyNEC, in process."""
    z = height_wl * C / FREQ_HZ
    ctx = nec_context()
    ctx.get_geometry().wire(
        1, SEGMENTS, -HALF_LENGTH_M, 0, z, HALF_LENGTH_M, 0, z, RADIUS_M, 1, 1
    )
    ctx.geometry_complete(-1)
    if sigma_s_per_m is None:
        ctx.gn_card(1, 0, 0, 0, 0, 0, 0, 0)
    else:
        ctx.gn_card(2, 0, EPS_R, sigma_s_per_m, 0, 0, 0, 0)
    ctx.ex_card(0, 1, SOURCE_SEGMENT, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, FREQ_HZ / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


def solvers(arguments):
    """PyNEC, plus binaries named as name=path or name=style:path."""
    found = [("PyNEC", pynec)]
    for argument in arguments:
        name, _, target = argument.partition("=")
        style, _, path = target.rpartition(":")
        style = style or DEFAULT_STYLE
        if not path or style not in STYLES:
            raise SystemExit(
                f"expected name=path or name=<{'|'.join(STYLES)}>:path, "
                f"got {argument!r}"
            )
        found.append(
            (
                name,
                lambda h, s, b=path, how=style: run_deck(b, deck(h, s), how),
            )
        )
    return found


def write_decks(directory):
    """Save every deck the sweep runs, as a pair per height.

    The runs themselves build decks in a temp directory and discard them.
    These are the same text, kept, so a result can be reproduced by hand or
    attached to a bug report without running this script.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for height_wl in HEIGHTS_WL:
        for label, sigma in (
            ("perfect", None),
            ("sigma1e10", SIGMA_LIMIT_S_PER_M),
        ):
            path = directory / f"dipole_{height_wl:g}wl_{label}.nec"
            path.write_text(deck(height_wl, sigma))
            written.append(path)
    return written


if __name__ == "__main__":
    arguments = list(sys.argv[1:])
    for argument in list(arguments):
        if argument.startswith("--decks="):
            arguments.remove(argument)
            paths = write_decks(argument.split("=", 1)[1])
            print(f"wrote {len(paths)} decks to {paths[0].parent}")

    found = solvers(arguments)

    print("Horizontal half-wave dipole, 145.9 MHz, centre fed, 11 segments.")
    print("GN 2 at sigma 1e10 against GN 1, as percent.  Both must agree,")
    print("so every cell is an error with a known correct value of zero.\n")
    print(f"{'height':>9}" + "".join(f"{name:>13}" for name, _ in found))

    for height_wl in HEIGHTS_WL:
        cells = ""
        for _, solve in found:
            try:
                perfect = solve(height_wl, None).real
                limit = solve(height_wl, SIGMA_LIMIT_S_PER_M).real
                cells += f"{100 * (limit - perfect) / perfect:+12.2f}%"
            except subprocess.CalledProcessError:
                # A solver that crashes has also failed to reach the limit.
                cells += f"{'crash':>13}"
        print(f"{height_wl:>8}wl{cells}")
