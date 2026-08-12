"""The fitted grid again, solved by NEC-4.2 instead of nec2++.

`sweep.py` produces the grid the shipped coefficients are fitted to, using
PyNEC.  `nec4_compare.py` measured how far NEC-4.2 differs over that same
grid and found the two agree to a couple of percent in the typical case
and part company in the tail, by about as much as the model's own error
bound.  That is enough to be worth refitting against, so this produces
the same grid from the solver that reaches the conductivity limit.

Output is `nec4_sweep.npz` in exactly the schema `sweep.npz` uses, so
`fit.py` and `coefficients.py` can read it by path and nothing else has
to change.

Parallelism is by (frequency, soil) rather than by point.  NEC-4 caches
its Sommerfeld grid in SOMD.NEC in the working directory and that grid is
a function of frequency and ground, so a worker that holds both fixed can
keep one directory and reuse the grid, which is most of why this is
affordable.  A worker that varied either would silently reuse the wrong
one.

    uv run python nec4_sweep.py /usr/bin/nec4d42
"""

import re
import subprocess
import sys
import tempfile
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import sweep
from nec_model import C, GROUNDS, end_fed_deck

OUTPUT = "nec4_sweep.npz"

#: The axes are sweep.py's, so the two grids are the same problem.
FREQS_HZ = sweep.FREQS_HZ
HEIGHTS_M = sweep.HEIGHTS_M
RETURNS_M = sweep.RETURNS_M
SOILS = tuple(sorted(GROUNDS))
RATIOS = np.arange(
    sweep.RATIO_MIN, sweep.RATIO_MAX + sweep.RATIO_STEP / 2, sweep.RATIO_STEP
)

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


def solve_group(job):
    """Every point at one frequency and soil, sharing one Sommerfeld grid."""
    binary, freq_hz, soil = job
    wavelength_m = C / freq_hz
    rows = []
    with tempfile.TemporaryDirectory(prefix="n4s-") as work:
        source = Path(work) / "in.nec"
        result = Path(work) / "out.txt"
        for height_m in HEIGHTS_M:
            for return_m in RETURNS_M:
                for ratio in RATIOS:
                    length_m = ratio * wavelength_m
                    source.write_text(
                        end_fed_deck(length_m, freq_hz, height_m, return_m, ground=soil)
                    )
                    try:
                        subprocess.run(
                            [binary, str(source), str(result)],
                            capture_output=True,
                            check=True,
                            cwd=work,
                        )
                        z = parse_impedance(result.read_text())
                    except (subprocess.CalledProcessError, ValueError, OSError):
                        # NaN rather than dying, as sweep.py does: a geometry
                        # the solver refuses should not lose the whole grid.
                        z = complex(np.nan, np.nan)
                    rows.append(
                        (
                            freq_hz,
                            height_m,
                            return_m,
                            SOILS.index(soil),
                            ratio,
                            z.real,
                            z.imag,
                        )
                    )
    return rows


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: nec4_sweep.py /path/to/nec4d42")
    binary = sys.argv[1]

    jobs = [(binary, freq, soil) for freq in FREQS_HZ for soil in SOILS]
    total = len(jobs) * len(HEIGHTS_M) * len(RETURNS_M) * len(RATIOS)
    print(
        f"{total} points over {len(FREQS_HZ)} freqs x {len(HEIGHTS_M)} heights "
        f"x {len(RETURNS_M)} returns x {len(SOILS)} soils x {len(RATIOS)} "
        f"lengths, in {len(jobs)} groups",
        flush=True,
    )

    start = time.time()
    with Pool(len(jobs)) as pool:
        collected = pool.map(solve_group, jobs)
    rows = [row for group in collected for row in group]
    elapsed = time.time() - start

    columns = np.array(rows)
    np.savez_compressed(
        OUTPUT,
        freq_hz=columns[:, 0],
        height_m=columns[:, 1],
        return_m=columns[:, 2],
        soil=columns[:, 3].astype(np.int8),
        ratio=columns[:, 4],
        resistance=columns[:, 5],
        reactance=columns[:, 6],
        soil_names=np.array(SOILS),
    )
    bad = int(np.isnan(columns[:, 5]).sum())
    print(f"done in {elapsed:.1f} s, {bad} failed, wrote {OUTPUT}")
