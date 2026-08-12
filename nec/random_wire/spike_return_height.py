"""Spike: can the two-line form carry counterpoise height as an axis?

The model holds the return 5 cm off the soil because NEC-2 must.  NEC-4
need not, so the height of the counterpoise could become a control --
from lying on the ground up to level with the wire, which spans the
thrown-out counterpoise, the raised radial and the elevated
counterpoise in one axis.

Two separate questions, and the spike answers both because they can fail
independently:

  form   given its own best coefficients, can the two-line form fit each
         return height at all?  If the per-group error grows with height
         the form is wrong there and no table rescues it.
  table  do the fitted coefficients move smoothly with return height?
         If they jump around, the axis cannot be interpolated and would
         need a solve per query.

`return_height_sweep.py` asked this against PyNEC over 0.01 to 3 m and
the answer was no: the form failed before the table did, x1.60 median at
a 2 m return.  Two things are different here.  The solver is NEC-4.2,
which is the better one in this regime and which fits about twice as
well below `h/lambda` 0.05.  And the axis is a fraction of the wire
height rather than an absolute height, which is the way a user would
describe it and keeps the geometry similar across the sweep.

The floor is 1 cm.  Below that NEC-4 breaks down -- at 1 mm a #14 wire
is 1.2 radii up and the answer leaves the trend -- and z = 0 exactly is
degenerate.  See ground_contact.py.

    uv run python spike_return_height.py /usr/bin/nec4d42
"""

import re
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from fit import PARAM_NAMES, fit_group
from nec_model import C, end_fed_deck

#: Small enough to be a spike.  Two bands well inside the fitted range,
#: three heights spanning it, one return length and one soil.
FREQS_HZ = (7.15e6, 14.175e6)
HEIGHTS_M = (3.0, 10.0, 20.0)
RETURN_M = 7.62
SOIL = "average"
RATIOS = np.arange(0.05, 2.0 + 1e-9, 0.05)

#: Counterpoise height as a fraction of the wire height, plus an absolute
#: floor for "on the ground".  0.9 rather than 1.0: at the wire's own
#: height there is no drop left, which is a different antenna.
FRACTIONS = (0.02, 0.05, 0.1, 0.25, 0.5, 0.9)
GROUND_M = 0.01

IMPEDANCE_FIELD = 4
SCIENTIFIC = re.compile(r"[-+]?\d*\.?\d+[Ee][-+]?\d+")


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


def return_heights(height_m):
    """Counterpoise heights under a wire at `height_m`, with their labels.

    Labelled by the step rather than by the achieved fraction: 1 cm is
    "on the ground" whether the wire is 3 m up or 20, and grouping by the
    fraction would split that row three ways.
    """
    return (("ground", GROUND_M),) + tuple((f"{f:g}h", f * height_m) for f in FRACTIONS)


def solve_group(job):
    """One (frequency, height, return height): the whole length axis."""
    binary, freq_hz, height_m, return_height_m, _ = job
    wavelength_m = C / freq_hz
    out = []
    with tempfile.TemporaryDirectory(prefix="srh-") as work:
        source = Path(work) / "in.nec"
        result = Path(work) / "out.txt"
        for ratio in RATIOS:
            source.write_text(
                end_fed_deck(
                    ratio * wavelength_m,
                    freq_hz,
                    height_m,
                    RETURN_M,
                    ground=SOIL,
                    return_height_m=return_height_m,
                )
            )
            try:
                subprocess.run(
                    [binary, str(source), str(result)],
                    capture_output=True,
                    check=True,
                    cwd=work,
                )
                out.append(parse_impedance(result.read_text()))
            except (subprocess.CalledProcessError, ValueError, OSError):
                out.append(complex(np.nan, np.nan))
    return job, np.array(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: spike_return_height.py /path/to/nec4d42")
    binary = sys.argv[1]

    jobs = [
        (binary, freq_hz, height_m, return_height_m, label)
        for freq_hz in FREQS_HZ
        for height_m in HEIGHTS_M
        for label, return_height_m in return_heights(height_m)
    ]
    print(f"{len(jobs)} groups x {len(RATIOS)} lengths, NEC-4.2\n", flush=True)

    start = time.time()
    with Pool(min(len(jobs), 14)) as pool:
        solved = pool.map(solve_group, jobs)
    print(f"solved in {time.time() - start:.0f} s\n")

    print(
        f"{'MHz':>7} {'h m':>5} {'ret z m':>8} {'z/h':>6} {'x err':>7} "
        + " ".join(f"{n:>8}" for n in PARAM_NAMES)
    )
    rows = []
    for (_, freq_hz, height_m, return_height_m, label), z in solved:
        good = np.isfinite(z.real)
        if good.sum() < 10:
            print(
                f"{freq_hz / 1e6:7.3f} {height_m:5g} {return_height_m:8.3f} {'':>6} {'refused':>7}"
            )
            continue
        wavelength_m = C / freq_hz
        # The return conductor is the drop that is left plus the run.
        total_return_m = (height_m - return_height_m) + RETURN_M
        params, err, _ = fit_group(
            RATIOS[good] * wavelength_m,
            np.full(good.sum(), total_return_m),
            wavelength_m,
            z[good],
        )
        rows.append((freq_hz, height_m, label, err, params))
        print(
            f"{freq_hz / 1e6:7.3f} {height_m:5g} {return_height_m:8.3f} "
            f"{return_height_m / height_m:6.3f} x{err:6.2f} "
            + " ".join(f"{v:8.4f}" for v in params)
        )

    print("\n-- can the form carry it? per-group error against z/h --")
    fractions = ["ground"] + [f"{f:g}h" for f in FRACTIONS]
    for fraction in fractions:
        errs = np.array([r[3] for r in rows if r[2] == fraction])
        print(
            f"  {fraction:>7}  median x{np.median(errs):.2f}  worst x{errs.max():.2f}"
        )

    print("\n-- could a table carry it? spread of each coefficient over z/h --")
    for i, name in enumerate(PARAM_NAMES):
        by_fraction = [
            np.median([r[4][i] for r in rows if r[2] == fraction])
            for fraction in fractions
        ]
        lo, hi = min(by_fraction), max(by_fraction)
        print(
            f"  {name:12} {lo:8.4f} to {hi:8.4f}   "
            f"x{hi / lo if lo > 0 else float('inf'):.2f} across the axis"
        )
