"""Sommerfeld ground near the interface: NEC-2 fails a limit it must meet.

Originally filed as a reproducer for a suspected nec2c bug, for
https://github.com/charlieh0tel/nec2c-js.  Running the `validation` branch
of https://github.com/KJ7LNW/nec2c and its FORTRAN reference binary turned
that diagnosis over, so this script now compares implementations.

## The test

As a soil's conductivity rises it becomes a perfect ground plane, so
`GN 2` must converge on the `GN 1` answer for the same geometry.  That
limit is exact physics, not a modelling judgement, and every
implementation computes the `GN 1` side identically.  A gap is therefore
the size of a fault in the Sommerfeld evaluation.

Below, with a return path 5 cm off the soil at 7.15 MHz -- 0.0012
wavelengths -- nec2++ converges to within 0.0 percent.  Every other
implementation stops about 30 percent above and stays there.

## What the fix does, and what it does not

Upstream found two genuine hand-transcription slips in `somnec.c`, both
on the Sommerfeld path:

  `a475aad` gshank's convergence gate computed `fabs(creal(a1) +
  fabs(cimag(a1)))`, one closing parenthesis too far right, so a signed
  real part was added to an imaginary magnitude before a single outer
  magnitude was taken.  The intended quantity is the L1 magnitude
  `|Re| + |Im|`, which FORTRAN GSHANK writes as two separate intrinsics.

  `3f16cbc` evlua closes the spectral integral with exactly one of two
  tail integrations, chosen by a GO TO ladder.  The port collapsed the
  ladder onto one reused flag, so on the large `rho/zph` branch both
  tails were skipped and the contour was left unfinished.

Both are real and both are fixed.  What they buy is fidelity to NEC-2,
which is measurable here: on the case below at sigma 1000, stock nec2c
reads 1867.6, the fixed build 1868.3, and `nec2dx` -- the original
FORTRAN, built from the same branch -- reads 1868.4.  The fix moves
nec2c onto the FORTRAN to five figures.

It does not move it onto the limit.  Fixed nec2c misses by the same 29.6
percent stock does, because that is what NEC-2 does.

## So the divergence is the method, not the port

`nec2dx` is the oracle: it is the FORTRAN every C and C++ port was
transcribed from.  On the half-wave dipole deck in
`nec2-js/investigations/`, at 0.02 wavelengths, stock nec2c reads +91.90
percent past the limit, fixed nec2c +91.92, and nec2dx +91.92.  aegnec2,
which links the original SOMNEC, reads +91.90.  The whole FORTRAN lineage
agrees with itself.

nec2++ is the outlier, at +0.77 percent, and it is the one that is right:
the limit has a known answer and only nec2++ reaches it.  What in nec2++
accounts for that is not established here -- the two somnec.c sites
upstream fixed read correctly in necpp today, so it is not those, and the
history between the two codebases has not been traced.  So the earlier
reading here -- "nec2c is buggy, nec2++ is correct" -- had the right
ranking for the wrong reason.

## nec2++ has an envelope too

It is better by about a decade in height, not unconditionally right.  On
that same dipole deck, with the fed element itself near the soil:

    0.02 wl    +0.77 %
    0.01 wl    -0.69 %
    0.005 wl   +8.2 %
    0.002 wl   +125.7 %

So nec2++ holds to roughly 0.005 wavelengths and then goes the way the
FORTRAN went, just later.  "Fitted against the implementation that
passes" is a statement about this geometry, which is measured below, and
not a general licence.

Two further limits on the reassurance.  The limit test only exercises the
high-conductivity corner: at sigma 1000 there is an exact answer to check
against, and at the sigma 0.005 of real soil there is none, so passing is
necessary rather than sufficient.  And a PyNEC-versus-binary check is not
independent -- PyNEC wraps this same nec2++, and the two agree here to
every figure printed, which shows only that the fit is reproducible.

## Why it matters here

`docs/random-wire.html` models a feedline lying on the soil, 5 cm up, and
its coefficients are fitted against nec2++, the implementation that
passes this test in exactly that geometry.

The consequence for the planned in-browser check is worse than it looked.
`nec2c-wasm` would disagree with the page's own coefficients by about 30
percent, for reasons invisible to the user -- and a fixed nec2c does not
lift that, because the gap is NEC-2's Sommerfeld evaluation rather than a
defect awaiting repair.  Only a nec2++ wasm build does.  See
docs/RANDOM_WIRE_TODO.md.

One caveat on how far to carry this.  The dipole deck puts the *fed*
element near the soil, and there no engine meets the limit below about
0.002 wavelengths.  Here the near-ground wire is the return and the
source sits 30 ft up, at 0.22 wavelengths, which is a milder case -- and
the measured pass is the evidence that it is mild enough.

## Running the comparison

PyNEC is always solved, in process.  External binaries are passed as
`name=path`, or `name=style:path` where the style is one of `flags`
(nec2c's `-i`/`-o`, the default), `attached` (`-iIN`, which nec2++ wants)
or `stdio`.  All are given a deck built to the same geometry:

    git clone https://github.com/KJ7LNW/nec2c && cd nec2c
    git checkout validation && ./autogen.sh && ./configure && make
    # builds ./nec2c and, on this branch, the FORTRAN ./nec2dx

    LD_LIBRARY_PATH=~/src/necpp/_install_/lib \\
    python nec2c_ground_bug.py \\
        nec2++=attached:~/src/necpp/_install_/bin/nec2++ \\
        stock=/path/to/master/nec2c \\
        fixed=/path/to/validation/nec2c \\
        fortran=/path/to/validation/nec2dx

`nec2dx` is the original NEC-2 FORTRAN, so it is the oracle rather than
another opinion: it is what every C and C++ port was transcribed from.

The style names match nec2-js/investigations/sommerfeld.mjs, which runs
the same limit against a half-wave dipole and sweeps height.  That is the
harness to reach for when the question is an implementation's envelope
rather than this particular installation.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

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

#: Impedance is the third pair of numbers on the source row of the ANTENNA
#: INPUT PARAMETERS table: voltage, current, impedance, admittance.
IMPEDANCE_FIELD = 4

#: Fields there can abut with no separating space when a value is negative,
#: so split on the exponent form rather than on whitespace.
SCIENTIFIC = re.compile(r"[-+]?\d*\.?\d+[Ee][-+]?\d+")


def wires(return_height_m=RETURN_HEIGHT_M):
    """The three wires, as (tag, segments, x1, y1, z1, x2, y2, z2)."""
    wavelength_m = C / FREQ_HZ
    return (
        (1, _segments(LENGTH_M, wavelength_m), 0, 0, HEIGHT_M, LENGTH_M, 0, HEIGHT_M),
        (
            2,
            _segments(HEIGHT_M - return_height_m, wavelength_m),
            0,
            0,
            HEIGHT_M,
            0,
            0,
            return_height_m,
        ),
        (
            3,
            _segments(RETURN_M, wavelength_m),
            0,
            0,
            return_height_m,
            RETURN_M,
            0,
            return_height_m,
        ),
    )


def zin(sigma_s_per_m=None, return_height_m=RETURN_HEIGHT_M):
    """Feedpoint Z via PyNEC.  sigma_s_per_m None means a perfect ground."""
    ctx = nec_context()
    geo = ctx.get_geometry()
    for tag, segments, x1, y1, z1, x2, y2, z2 in wires(return_height_m):
        geo.wire(tag, segments, x1, y1, z1, x2, y2, z2, WIRE_RADIUS_M, 1, 1)
    ctx.geometry_complete(1)
    if sigma_s_per_m is None:
        ctx.gn_card(1, 0, 0, 0, 0, 0, 0, 0)
    else:
        ctx.gn_card(2, 0, EPS_R, sigma_s_per_m, 0, 0, 0, 0)
    ctx.ex_card(0, 1, 1, 0, 1.0, 0, 0, 0, 0, 0)
    ctx.fr_card(0, 1, FREQ_HZ / 1e6, 0)
    ctx.xq_card(0)
    return ctx.get_input_parameters(0).get_impedance()[0]


def deck(sigma_s_per_m=None, return_height_m=RETURN_HEIGHT_M):
    """The same geometry as a NEC card deck, for an external solver."""
    lines = ["CM conductivity limit, end-fed wire with return near ground", "CE"]
    for tag, segments, x1, y1, z1, x2, y2, z2 in wires(return_height_m):
        lines.append(
            f"GW {tag} {segments} {x1:g} {y1:g} {z1:g} "
            f"{x2:g} {y2:g} {z2:g} {WIRE_RADIUS_M:g}"
        )
    lines.append("GE 1")
    if sigma_s_per_m is None:
        lines.append("GN 1")
    else:
        lines.append(f"GN 2 0 0 0 {EPS_R:g} {sigma_s_per_m:g}")
    lines += ["EX 0 1 1 0 1.0 0.0", f"FR 0 1 0 0 {FREQ_HZ / 1e6:g} 0", "XQ", "EN"]
    return "\n".join(lines) + "\n"


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


#: NEC implementations disagree about how to be invoked.  Each entry turns a
#: scratch directory into the argv to use, and where to read the report from;
#: None means the report comes back on stdout.  Same names as the styles in
#: nec2-js/investigations/sommerfeld.mjs, so the two harnesses agree.
STYLES = {
    "flags": lambda source, out: ([("-i"), str(source), "-o", str(out)], out),
    "attached": lambda source, out: ([f"-i{source}", f"-o{out}"], out),
    "stdio": lambda source, out: ([], None),
}
DEFAULT_STYLE = "flags"


def run_deck(binary, text, style=DEFAULT_STYLE):
    """Solve a deck with an external NEC binary."""
    with tempfile.TemporaryDirectory() as work:
        source = Path(work) / "case.nec"
        source.write_text(text)
        args, out = STYLES[style](source, Path(work) / "case.out")
        done = subprocess.run(
            [binary, *args],
            input=None if out else text.encode(),
            check=True,
            capture_output=True,
        )
        return parse_impedance(out.read_text() if out else done.stdout.decode())


def solvers(arguments):
    """PyNEC, plus binaries named as name=path or name=style:path.

    Style defaults to nec2c's -i/-o; nec2++ wants `attached` and Fortran
    NEC-2 builds usually want `stdio`.
    """
    found = [("PyNEC", lambda **kw: zin(**kw))]
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
                lambda binary=path, how=style, **kw: run_deck(binary, deck(**kw), how),
            ),
        )
    return found


if __name__ == "__main__":
    found = solvers(sys.argv[1:])
    names = [name for name, _ in found]

    print("107 ft wire 30 ft up, 25 ft return 5 cm off soil, 7.15 MHz,")
    print(f"eps_r {EPS_R:g}.  |Z| ohms, and the gap from each perfect-ground")
    print("column, which is where a rising conductivity must land.\n")

    perfect = {name: abs(solve(sigma_s_per_m=None)) for name, solve in found}
    header = "".join(f"{name:>22}" for name in names)
    print(f"{'sigma S/m':>10}{header}")
    for sigma in SIGMAS_S_PER_M:
        cells = ""
        for name, solve in found:
            value = abs(solve(sigma_s_per_m=sigma))
            cells += f"{value:14.1f}{100 * (value / perfect[name] - 1):+7.1f}%"
        print(f"{sigma:10g}{cells}")
    print(
        f"{'perfect':>10}" + "".join(f"{perfect[n]:14.1f}{0.0:+7.1f}%" for n in names)
    )

    print("\nExpected: every last row sits on its own perfect-ground row,")
    print("which is exact physics.  Only nec2++ gets there.  The FORTRAN")
    print("and both nec2c builds stop about 30 percent above, so the gap is")
    print("NEC-2's Sommerfeld evaluation and not a defect in the port.")

    print("\nSame check with the return lifted clear of the interface,")
    print("where the implementations already agreed:")
    print(f"{'return h m':>10}" + header)
    for return_height_m in (0.05, 0.5, 2.0):
        cells = ""
        for _, solve in found:
            cells += f"{abs(solve(sigma_s_per_m=0.03, return_height_m=return_height_m)):21.1f}"
        print(f"{return_height_m:10g}{cells}")
