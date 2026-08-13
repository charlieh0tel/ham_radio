"""Coefficients over h/lambda and counterpoise height, refined jointly.

`table2d.py` established that the second axis earns its place -- it takes
the 90th percentile from x1.65 to x1.38 and the worst from x3.11 to
x1.62 -- and settled two things about its shape.  Only `alpha_r`, `vf_r`
and `kr` need it, because they describe the return line and it is the
return line that moves; giving `alpha_a` and `ka` the axis changes
nothing.  And four nodes carry it as well as six.

That matters because the refinement has to move every parameter at once.
`coefficients.py` refines 40 per soil and its docstring notes that 120
struggles; the full 2-D table would be 200.  Return-only at four nodes is
112, which is why the shape was worth measuring before building.

Refinement is the point of this module rather than a flourish.
`alpha_r`, `vf_r` and `kr` trade off against one another, so a table
built from coordinate-wise medians can sit outside the joint feasible
set -- each entry sensible, the vector not a fit of anything.

    uv run python coefficients2d.py                    # the flat top
    uv run python coefficients2d.py --sweep nec4_sloper_sweep.npz
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from coefficients import MIN_H_OVER_LAMBDA, NODES, REFINE_BOUNDS, TABLE_PARAMS, VF_A
from fit import fit_group, model_zin
from nec_model import BALUN_HEIGHT_M, C
from table2d import RETURN_ONLY, build, look_up

#: What differs between the two geometries, and all that differs: which
#: column holds the height the table is indexed on, and what the return
#: conductor drops from.  A flat top drops from the wire; a sloper from
#: the balun, which is where it is fed.
FLAT_TOP = ("height_m", None)
SLOPER = ("apex_m", BALUN_HEIGHT_M)

#: Counterpoise height in wavelengths.  Four nodes, log spaced over what
#: a real installation reaches, held flat outside as h/lambda is.
Z_NODES = np.array([1e-4, 1e-3, 8e-3, 6e-2])

#: Written beside this script, as coefficients.json is, so the shipped
#: numbers have a checkable original outside the page.
DATA = Path(__file__).resolve().parent / "coefficients2d.json"

#: Indices into TABLE_PARAMS that carry the second axis.
TWO_D = RETURN_ONLY
ONE_D = tuple(i for i in range(len(TABLE_PARAMS)) if i not in TWO_D)


def pack(block):
    """A soil's table as a flat vector: the 1-D coefficients, then the 2-D."""
    flat = [block[:, 0, pi] for pi in ONE_D]
    flat += [block[:, :, pi].reshape(-1) for pi in TWO_D]
    return np.concatenate(flat)


def unpack(flat):
    """The inverse, rebuilding the (h-node, z-node, parameter) block."""
    block = np.zeros((len(NODES), len(Z_NODES), len(TABLE_PARAMS)))
    at = 0
    for pi in ONE_D:
        block[:, :, pi] = flat[at : at + len(NODES)][:, np.newaxis]
        at += len(NODES)
    for pi in TWO_D:
        block[:, :, pi] = flat[at : at + len(NODES) * len(Z_NODES)].reshape(
            len(NODES), len(Z_NODES)
        )
        at += len(NODES) * len(Z_NODES)
    return block


def bounds():
    """REFINE_BOUNDS, laid out to match `pack`."""
    lo = [np.full(len(NODES), REFINE_BOUNDS[0][pi]) for pi in ONE_D]
    hi = [np.full(len(NODES), REFINE_BOUNDS[1][pi]) for pi in ONE_D]
    lo += [np.full(len(NODES) * len(Z_NODES), REFINE_BOUNDS[0][pi]) for pi in TWO_D]
    hi += [np.full(len(NODES) * len(Z_NODES), REFINE_BOUNDS[1][pi]) for pi in TWO_D]
    return np.concatenate(lo), np.concatenate(hi)


def slices(data, si, geometry, min_points=1):
    """Every group for one soil, as the refinement and the fits want them."""
    height_key, feed_m = geometry
    rows = []
    for freq_hz, height_m, step in itertools.product(
        np.unique(data["freq_hz"]),
        np.unique(data[height_key]),
        np.unique(data["step"]),
    ):
        sel = (
            (data["freq_hz"] == freq_hz)
            & (data[height_key] == height_m)
            & (data["soil"] == si)
            & (data["step"] == step)
            & np.isfinite(data["resistance"])
        )
        if sel.sum() < min_points:
            continue
        wavelength_m = C / freq_hz
        if height_m / wavelength_m < MIN_H_OVER_LAMBDA:
            continue
        z_m = float(np.unique(data["return_height_m"][sel])[0])
        drops_from_m = height_m if feed_m is None else feed_m
        rows.append(
            (
                height_m / wavelength_m,
                z_m / wavelength_m,
                data["ratio"][sel] * wavelength_m,
                (drops_from_m - data["return_height_m"][sel]) + data["return_m"][sel],
                wavelength_m,
                data["resistance"][sel] + 1j * data["reactance"][sel],
            )
        )
    return rows


def fit_groups(data, geometry):
    """Per-group fits, in the shape build() wants."""
    out = []
    for si in range(len(data["soil_names"])):
        for h_lam, z_lam, length_m, total_return_m, wavelength_m, z_nec in slices(
            data, si, geometry, min_points=20
        ):
            params, _, _ = fit_group(length_m, total_return_m, wavelength_m, z_nec)
            out.append({"soil": si, "h_lam": h_lam, "z_lam": z_lam, "params": params})
    return out


def refine(table, data, geometry, max_nfev=600):
    """Fit the tabulated surface itself, one soil at a time."""
    refined = table.copy()
    lo, hi = bounds()
    for si in range(table.shape[0]):
        rows = slices(data, si, geometry)

        def residual(flat, rows=rows):
            block = unpack(flat)[np.newaxis]
            out = []
            for h_lam, z_lam, length_m, total_return_m, wavelength_m, z_nec in rows:
                alpha_a, ka, alpha_r, vf_r, kr = look_up(
                    block, 0, h_lam, Z_NODES, z_lam
                )
                model = model_zin(
                    (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
                    length_m,
                    total_return_m,
                    wavelength_m,
                )
                magnitude = np.log(np.abs(model)) - np.log(np.abs(z_nec))
                phase = np.angle(model) - np.angle(z_nec)
                phase = (phase + np.pi) % (2.0 * np.pi) - np.pi
                out.append(np.concatenate([magnitude, phase]))
            return np.concatenate(out)

        start = np.clip(pack(refined[si]), lo, hi)
        out = least_squares(residual, start, bounds=(lo, hi), max_nfev=max_nfev)
        refined[si] = unpack(out.x)
    return refined


def measure(data, table, geometry):
    """Tabulated error over every group, as coefficients.py measures it."""
    factors = []
    for si in range(len(data["soil_names"])):
        for h_lam, z_lam, length_m, total_return_m, wavelength_m, z_nec in slices(
            data, si, geometry
        ):
            alpha_a, ka, alpha_r, vf_r, kr = look_up(table, si, h_lam, Z_NODES, z_lam)
            model = model_zin(
                (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
                length_m,
                total_return_m,
                wavelength_m,
            )
            err = np.log(np.abs(model)) - np.log(np.abs(z_nec))
            factors.append(np.exp(np.sqrt(np.mean(err**2))))
    return np.array(factors)


def report(name, factors):
    print(
        f"  {name:<12} n={len(factors):4d}  median x{np.median(factors):.2f}  "
        f"90th x{np.percentile(factors, 90):.2f}  worst x{factors.max():.2f}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sweep", default="nec4_return_height_sweep.npz")
    parser.add_argument("--max-nfev", type=int, default=600)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the fitted table into coefficients2d.json",
    )
    args = parser.parse_args()

    data = np.load(args.sweep, allow_pickle=False)
    geometry = SLOPER if "apex_m" in data.files else FLAT_TOP
    print(f"{args.sweep}: {'sloper' if geometry is SLOPER else 'flat top'}\n")

    groups = fit_groups(data, geometry)
    print(f"{len(groups)} groups fitted\n")
    table = build(groups, len(data["soil_names"]), "z_lam", Z_NODES, TWO_D)
    report("unrefined", measure(data, table, geometry))
    table = refine(table, data, geometry, args.max_nfev)
    factors = measure(data, table, geometry)
    report("refined", factors)

    if args.write:
        name = "sloper" if geometry is SLOPER else "flat_top"
        DATA.parent.mkdir(exist_ok=True)
        existing = json.loads(DATA.read_text()) if DATA.exists() else {}
        existing.update(
            {
                "h_nodes": NODES.tolist(),
                "z_nodes": Z_NODES.tolist(),
                "params": list(TABLE_PARAMS),
                "two_d_params": [TABLE_PARAMS[i] for i in TWO_D],
                "vf_a": VF_A,
                "soils": [str(s) for s in data["soil_names"]],
                name: {
                    "table": table.tolist(),
                    "error": {
                        "median": float(np.median(factors)),
                        "p90": float(np.percentile(factors, 90)),
                        "worst": float(factors.max()),
                    },
                },
            }
        )
        DATA.write_text(json.dumps(existing, indent=1) + "\n")
        print(f"\nwrote {name} into {DATA.name}")
