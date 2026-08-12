"""Counterpoise height as a fourth axis, solved by NEC-4.2 and evaluated.

`spike_return_height.py` established that the two-line form carries this
axis -- per-group error x1.13 at the ground to x1.19 at half the wire
height -- on two frequencies and one soil.  This asks the same question
on the axes the coefficient table actually indexes, which is what decides
whether the axis can ship.

Sizing.  The full grid crossed with seven counterpoise heights is about
748,000 points and nine hours.  Everything the table indexes is kept
whole -- frequency, wire height, soil -- and the two axes it does not are
trimmed: return length from seven values to three, and the length step
from 0.025 to 0.05 wavelengths.  Return length enters the model
analytically through the total conductor rather than as a table axis, and
0.05 is still twice the resolution the spike fitted cleanly on.

Two questions, reported separately because they fail separately:

  form   given its own best coefficients, does each group still fit?
  table  do the coefficients move smoothly enough along the new axis to
         interpolate, as they do along h/lambda?

    uv run python nec4_return_height_sweep.py /usr/bin/nec4d42
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
from fit import PARAM_NAMES, fit_group
from nec_model import C, GROUNDS, end_fed_deck

OUTPUT = "nec4_return_height_sweep.npz"

FREQS_HZ = sweep.FREQS_HZ
HEIGHTS_M = sweep.HEIGHTS_M
SOILS = tuple(sorted(GROUNDS))

#: Trimmed: short, default and long.  See the module docstring.
RETURNS_M = (4.0, 7.62, 20.0)
RATIOS = np.arange(0.05, 4.0 + 1e-9, 0.05)

#: Counterpoise height as a fraction of the wire height, plus a floor for
#: lying on the ground.  0.9 is omitted: with almost no drop left it is a
#: different antenna, and it is the only step the spike saw degrade.
FRACTIONS = (0.02, 0.05, 0.1, 0.25, 0.5)
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


def steps(height_m):
    """Counterpoise heights under a wire at `height_m`, with their labels."""
    return (("ground", GROUND_M),) + tuple((f"{f:g}h", f * height_m) for f in FRACTIONS)


def solve_group(job):
    """One (frequency, soil): every height, return, step and length in it.

    Grouped this way because NEC-4 caches its Sommerfeld grid per working
    directory and that grid is a function of frequency and ground alone.
    """
    binary, freq_hz, soil = job
    wavelength_m = C / freq_hz
    rows = []
    with tempfile.TemporaryDirectory(prefix="rhs-") as work:
        source = Path(work) / "in.nec"
        result = Path(work) / "out.txt"
        for height_m in HEIGHTS_M:
            for label, return_height_m in steps(height_m):
                for return_m in RETURNS_M:
                    for ratio in RATIOS:
                        source.write_text(
                            end_fed_deck(
                                ratio * wavelength_m,
                                freq_hz,
                                height_m,
                                return_m,
                                ground=soil,
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
                            z = parse_impedance(result.read_text())
                        except (subprocess.CalledProcessError, ValueError, OSError):
                            z = complex(np.nan, np.nan)
                        rows.append(
                            (
                                freq_hz,
                                height_m,
                                return_m,
                                SOILS.index(soil),
                                ratio,
                                return_height_m,
                                FRACTIONS.index(float(label[:-1]))
                                if label != "ground"
                                else -1,
                                z.real,
                                z.imag,
                            )
                        )
    return rows


def evaluate(data):
    """Fit each group and report whether form and table survive the axis."""
    labels = ["ground"] + [f"{f:g}h" for f in FRACTIONS]
    step_index = data["step"]
    rows = []
    for si in range(len(SOILS)):
        for freq_hz in FREQS_HZ:
            for height_m in HEIGHTS_M:
                for index, label in zip([-1] + list(range(len(FRACTIONS))), labels):
                    sel = (
                        (data["freq_hz"] == freq_hz)
                        & (data["height_m"] == height_m)
                        & (data["soil"] == si)
                        & (step_index == index)
                        & np.isfinite(data["resistance"])
                    )
                    if sel.sum() < 20:
                        continue
                    wavelength_m = C / freq_hz
                    total_return_m = (height_m - data["return_height_m"][sel]) + data[
                        "return_m"
                    ][sel]
                    params, err, _ = fit_group(
                        data["ratio"][sel] * wavelength_m,
                        total_return_m,
                        wavelength_m,
                        data["resistance"][sel] + 1j * data["reactance"][sel],
                    )
                    rows.append((label, height_m / wavelength_m, err, params))

    print("\n-- can the form carry it? per-group error, by counterpoise height --")
    for label in labels:
        errs = np.array([r[2] for r in rows if r[0] == label])
        inside = np.array([r[2] for r in rows if r[0] == label and r[1] >= 0.05])
        if not len(errs):
            continue
        print(
            f"  {label:>7}  all n={len(errs):3d} median x{np.median(errs):.2f} "
            f"90th x{np.percentile(errs, 90):.2f}   "
            f"h/lam>=0.05 median x{np.median(inside):.2f} "
            f"90th x{np.percentile(inside, 90):.2f}"
        )

    print("\n-- could a table carry it? median coefficient at each step --")
    print(f"{'step':>7} " + " ".join(f"{n:>11}" for n in PARAM_NAMES))
    for label in labels:
        picked = [r[3] for r in rows if r[0] == label]
        if not picked:
            continue
        median = np.median(np.array(picked), axis=0)
        print(f"{label:>7} " + " ".join(f"{v:11.4f}" for v in median))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: nec4_return_height_sweep.py /path/to/nec4d42")
    binary = sys.argv[1]

    jobs = [(binary, freq, soil) for freq in FREQS_HZ for soil in SOILS]
    per_group = len(HEIGHTS_M) * (1 + len(FRACTIONS)) * len(RETURNS_M) * len(RATIOS)
    print(f"{len(jobs) * per_group} points in {len(jobs)} groups", flush=True)

    start = time.time()
    with Pool(len(jobs)) as pool:
        collected = pool.map(solve_group, jobs)
    columns = np.array([row for group in collected for row in group])
    print(f"solved in {time.time() - start:.0f} s", flush=True)

    np.savez_compressed(
        OUTPUT,
        freq_hz=columns[:, 0],
        height_m=columns[:, 1],
        return_m=columns[:, 2],
        soil=columns[:, 3].astype(np.int8),
        ratio=columns[:, 4],
        return_height_m=columns[:, 5],
        step=columns[:, 6].astype(np.int8),
        resistance=columns[:, 7],
        reactance=columns[:, 8],
        soil_names=np.array(SOILS),
    )
    bad = int(np.isnan(columns[:, 7]).sum())
    print(f"{bad} failed, wrote {OUTPUT}")

    evaluate(np.load(OUTPUT, allow_pickle=False))
