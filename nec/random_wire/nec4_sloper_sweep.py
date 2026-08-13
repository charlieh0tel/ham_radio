"""The sloper geometry, swept and fitted the way the flat top was.

`slope_check.py` established that a sloper is not a flat top at any
equivalent height, and that no remapping rescues it.  What it did not ask
is whether the *two-line form* covers a sloper once refitted, which is a
different question and the one that decides how much work this is.

The return line is already settled.  A sloper's balun height is the drop,
the drop is part of the return conductor, and the model solves the whole
conductor analytically -- holding it fixed while moving the balun over
the whole stake-to-reach range moves the feedpoint by at most 1.08x.  So
the return needs nothing new, and the balun is pinned at
`nec_model.BALUN_HEIGHT_M`.

That leaves one question.  The antenna line is a slanting wire rather
than a horizontal one, so:

  form   does the two-line form still fit each group?
  table  do the antenna-line coefficients differ enough from the flat
         top's to need their own table, or does the existing one cover
         both?

The counterpoise-height axis is narrower here than on a flat top.  The
counterpoise leaves the balun, so it runs from the ground up to the balun
rather than up to the wire.

A sloper's wire must be longer than the rise it climbs, so the length
axis is truncated -- severely for a high apex on a high band.  Points
that cannot be built are skipped rather than modelled.

    uv run python nec4_sloper_sweep.py /usr/bin/nec4d42
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
from nec_model import BALUN_HEIGHT_M, C, GROUNDS, sloper_deck

OUTPUT = "nec4_sloper_sweep.npz"

FREQS_HZ = sweep.FREQS_HZ
APEXES_M = sweep.HEIGHTS_M
SOILS = tuple(sorted(GROUNDS))
RETURNS_M = (4.0, 7.62, 20.0)
RATIOS = np.arange(0.05, 4.0 + 1e-9, 0.05)

#: Counterpoise heights: on the ground, up to level with the balun.
RETURN_HEIGHTS_M = (0.01, 0.15, 0.30, 0.45, BALUN_HEIGHT_M)

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
    """One (frequency, soil), which is what the Sommerfeld cache allows."""
    binary, freq_hz, soil = job
    wavelength_m = C / freq_hz
    rows = []
    with tempfile.TemporaryDirectory(prefix="sls-") as work:
        source = Path(work) / "in.nec"
        result = Path(work) / "out.txt"
        for apex_m in APEXES_M:
            if apex_m <= BALUN_HEIGHT_M:
                continue
            for index, return_height_m in enumerate(RETURN_HEIGHTS_M):
                for return_m in RETURNS_M:
                    for ratio in RATIOS:
                        deck = sloper_deck(
                            ratio * wavelength_m,
                            freq_hz,
                            apex_m,
                            return_m,
                            ground=soil,
                            return_height_m=return_height_m,
                        )
                        if deck is None:
                            continue
                        source.write_text(deck)
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
                                apex_m,
                                return_m,
                                SOILS.index(soil),
                                ratio,
                                return_height_m,
                                index,
                                z.real,
                                z.imag,
                            )
                        )
    return rows


def evaluate(data):
    """Fit each group; report whether the form holds and how it compares."""
    rows = []
    for si in range(len(SOILS)):
        for freq_hz in FREQS_HZ:
            for apex_m in APEXES_M:
                for index, return_height_m in enumerate(RETURN_HEIGHTS_M):
                    sel = (
                        (data["freq_hz"] == freq_hz)
                        & (data["apex_m"] == apex_m)
                        & (data["soil"] == si)
                        & (data["step"] == index)
                        & np.isfinite(data["resistance"])
                    )
                    if sel.sum() < 20:
                        continue
                    wavelength_m = C / freq_hz
                    total_return_m = (
                        BALUN_HEIGHT_M - data["return_height_m"][sel]
                    ) + data["return_m"][sel]
                    params, err, _ = fit_group(
                        data["ratio"][sel] * wavelength_m,
                        total_return_m,
                        wavelength_m,
                        data["resistance"][sel] + 1j * data["reactance"][sel],
                    )
                    rows.append((return_height_m, apex_m / wavelength_m, err, params))

    print(f"\n{len(rows)} groups fitted\n")
    print("-- can the form carry a sloper? per-group error --")
    for return_height_m in RETURN_HEIGHTS_M:
        errs = np.array([r[2] for r in rows if r[0] == return_height_m])
        if not len(errs):
            continue
        print(
            f"  counterpoise at {return_height_m:5.2f} m  n={len(errs):3d}  "
            f"median x{np.median(errs):.2f}  90th x{np.percentile(errs, 90):.2f}  "
            f"worst x{errs.max():.2f}"
        )
    allerr = np.array([r[2] for r in rows])
    print(
        f"  {'overall':>21}  n={len(allerr):3d}  median x{np.median(allerr):.2f}  "
        f"90th x{np.percentile(allerr, 90):.2f}  worst x{allerr.max():.2f}"
    )

    print("\n-- how do the coefficients sit? median at each counterpoise height --")
    print(f"{'cp m':>6} " + " ".join(f"{n:>11}" for n in PARAM_NAMES))
    for return_height_m in RETURN_HEIGHTS_M:
        picked = [r[3] for r in rows if r[0] == return_height_m]
        if not picked:
            continue
        median = np.median(np.array(picked), axis=0)
        print(f"{return_height_m:6.2f} " + " ".join(f"{v:11.4f}" for v in median))

    print("\nFlat top, for comparison (from nec4_return_height_sweep.py):")
    print(
        f"{'ground':>6}      0.1168      1.0000      0.7780      "
        f"0.5383      0.8244      0.7698"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: nec4_sloper_sweep.py /path/to/nec4d42")
    binary = sys.argv[1]

    jobs = [(binary, freq, soil) for freq in FREQS_HZ for soil in SOILS]
    print(
        f"{len(jobs)} groups, up to "
        f"{len(APEXES_M) * len(RETURN_HEIGHTS_M) * len(RETURNS_M) * len(RATIOS)} "
        f"points each before unbuildable ones are skipped",
        flush=True,
    )

    start = time.time()
    with Pool(len(jobs)) as pool:
        collected = pool.map(solve_group, jobs)
    columns = np.array([row for group in collected for row in group])
    print(f"{len(columns)} solved in {time.time() - start:.0f} s", flush=True)

    np.savez_compressed(
        OUTPUT,
        freq_hz=columns[:, 0],
        apex_m=columns[:, 1],
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
