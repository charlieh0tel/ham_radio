"""Collapse the per-group fits into the table the page carries.

Run with --write to patch docs/random-wire.html in place, between its
BEGIN and END GENERATED COEFFICIENTS markers.  The constants were
hand-copied once, which needed a separate script to verify; generating
them removes both the transcription step and the need to check it.


The x1.35 bound belongs to coefficients fitted independently for every
frequency, height and soil.  The page cannot do that: it gets a small
table and interpolates.  So the number worth quoting is the error of the
*tabulated* model, measured here against the whole sweep rather than
inherited from the per-group fit.

Coefficients are tabulated against log10(h/lambda), which is the variable
they actually move with, and against soil.  vf_a is not tabulated: it
fits to 1.000 in every bin, so it ships as a constant.

Emits a JavaScript block for pasting into random-wire.html.
"""

import argparse
import itertools
import json
import re
from pathlib import Path

import numpy as np

from scipy.optimize import least_squares

from fit import fit_group, load, model_zin
from nec_model import C

#: Below this the model is not fitted at all.  Two independent failures
#: live there and neither is the model's: NEC returns non-physical negative
#: resistances, and the per-wire segment floor puts 12:1 grading on the
#: junction carrying the source, which does not converge away.  Both are
#: caused by the drop being short in wavelengths, which is what a low
#: h/lambda is.  Fitting through them was making the coefficients describe
#: the solver rather than the antenna.
#:
#: The floor is 0.05 because that is where the page already stops claiming
#: accuracy -- MODEL_BOUND_H_OVER_LAM -- and because it is exactly where the
#: bad data ends: at 0.02 some 327 non-physical points survive, 23 percent of
#: one group at 1.9 MHz over poor ground, while at 0.05 there are none.
#: Fitting where the page claims accuracy and extrapolating flat below it is
#: the same statement made once instead of twice.
MIN_H_OVER_LAMBDA = 0.05

#: Nodes in h/lambda.  Spaced logarithmically over the range a real
#: installation reaches, from the exclusion floor to 25 m on 10 m.  Below
#: the first node the table is held flat, which is honest extrapolation
#: rather than a fit to points NEC could not solve.
NODES = np.array([0.05, 0.09, 0.16, 0.28, 0.5, 0.9, 1.6, 2.5])

#: Tabulated per soil per node.  vf_a is constant, see module docstring.
TABLE_PARAMS = ("alpha_a_lam", "ka", "alpha_r_lam", "vf_r", "kr")

#: Bounds for the joint refinement, in TABLE_PARAMS order, taken from the span
#: the per-group fits reach and rounded outwards.  Left at fit.py's much looser
#: search bounds the refinement buys accuracy by pushing a Z0 scale to 2.7,
#: which is a line form that has stopped describing a wire: the table would be
#: compensating for the model rather than fitting the antenna.  Plausibility is
#: asserted again on the far side, in docs/tools/model.test.mjs.
REFINE_BOUNDS = (
    (0.02, 0.4, 0.05, 0.35, 0.4),
    (0.40, 1.6, 3.00, 1.00, 1.6),
)
VF_A = 1.0

#: Fitted-parameter index of each tabulated name, into fit.PARAM_NAMES.
SOURCE_INDEX = (0, 2, 3, 4, 5)


def fitted_groups(d, z):
    """Per-group fits, tagged with h/lambda and soil.

    Groups below MIN_H_OVER_LAMBDA are skipped entirely rather than fitted
    and down-weighted: the data there is the solver's, not the antenna's.
    """
    out = []
    for freq, height, si in itertools.product(
        np.unique(d["freq_hz"]), np.unique(d["height_m"]), range(len(d["soil_names"]))
    ):
        wavelength_m = C / freq
        if height / wavelength_m < MIN_H_OVER_LAMBDA:
            continue
        sel = (d["freq_hz"] == freq) & (d["height_m"] == height) & (d["soil"] == si)
        params, _, _ = fit_group(
            d["ratio"][sel] * wavelength_m,
            height + d["return_m"][sel],
            wavelength_m,
            z[sel],
        )
        out.append((height / wavelength_m, si, params))
    return out


def build_table(groups, n_soils):
    """Median fitted value per soil per node, weighted by log-distance.

    Groups do not land on the nodes, so each node takes a weighted median
    of nearby groups.  Weights fall off over half a decade, wide enough
    that every node sees several groups and narrow enough to keep the
    trend.
    """
    table = np.zeros((n_soils, len(NODES), len(TABLE_PARAMS)))
    for si in range(n_soils):
        mine = [(h, p) for h, s, p in groups if s == si]
        h_lam = np.array([h for h, _ in mine])
        params = np.array([p for _, p in mine])
        for ni, node in enumerate(NODES):
            weight = np.exp(-((np.log10(h_lam / node) / 0.5) ** 2))
            for pi, source in enumerate(SOURCE_INDEX):
                order = np.argsort(params[:, source])
                cumulative = np.cumsum(weight[order])
                mid = np.searchsorted(cumulative, cumulative[-1] / 2.0)
                table[si, ni, pi] = params[order, source][mid]
    return table


def refine_table(table, d, z, soils, max_nfev=400):
    """Fit the tabulated surface itself against the sweep.

    build_table takes a weighted median of each parameter independently, so a
    node's five values can come from five different groups.  alpha_r, vf_r and
    kr trade off strongly against one another, and a coordinate-wise median of
    quantities that trade off need not be a fit of anything -- the shipped
    vector can sit outside the joint feasible set.

    The error is measured on the tabulated model anyway, so it is the thing to
    optimise.  This takes the median table as a starting point, which is close
    enough to converge quickly, and refines it against the same residual the
    per-group fits use.  One soil at a time: soils do not interact, and 40
    parameters converges where 120 struggles.
    """
    refined = table.copy()
    for si in range(len(soils)):
        rows = []
        for freq, height in itertools.product(
            np.unique(d["freq_hz"]), np.unique(d["height_m"])
        ):
            if height / (C / freq) < MIN_H_OVER_LAMBDA:
                continue
            sel = (d["freq_hz"] == freq) & (d["height_m"] == height) & (d["soil"] == si)
            if not sel.any():
                continue
            wavelength_m = C / freq
            rows.append(
                (
                    height / wavelength_m,
                    d["ratio"][sel] * wavelength_m,
                    height + d["return_m"][sel],
                    wavelength_m,
                    z[sel],
                )
            )

        def residual(flat, rows=rows):
            block = flat.reshape(len(NODES), len(TABLE_PARAMS))
            out = []
            for h_over_lam, length_m, total_return_m, wavelength_m, z_nec in rows:
                alpha_a, ka, alpha_r, vf_r, kr = interpolate(
                    block[np.newaxis, :, :], 0, h_over_lam
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

        lo = np.tile(REFINE_BOUNDS[0], len(NODES))
        hi = np.tile(REFINE_BOUNDS[1], len(NODES))
        start = np.clip(refined[si].reshape(-1), lo, hi)
        out = least_squares(residual, start, bounds=(lo, hi), max_nfev=max_nfev)
        refined[si] = out.x.reshape(len(NODES), len(TABLE_PARAMS))
    return refined


def interpolate(table, soil_index, h_over_lam):
    """Table lookup, linear in log10(h/lambda), clamped at the ends."""
    x = np.log10(np.clip(h_over_lam, NODES[0], NODES[-1]))
    nodes = np.log10(NODES)
    return np.array(
        [
            np.interp(x, nodes, table[soil_index, :, pi])
            for pi in range(len(TABLE_PARAMS))
        ]
    )


def tabulated_error(d, z, table):
    """Error of the tabulated model over every point in the sweep."""
    factors = []
    for freq, height, si in itertools.product(
        np.unique(d["freq_hz"]), np.unique(d["height_m"]), range(len(d["soil_names"]))
    ):
        sel = (d["freq_hz"] == freq) & (d["height_m"] == height) & (d["soil"] == si)
        wavelength_m = C / freq
        alpha_a, ka, alpha_r, vf_r, kr = interpolate(table, si, height / wavelength_m)
        model = model_zin(
            (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
            d["ratio"][sel] * wavelength_m,
            height + d["return_m"][sel],
            wavelength_m,
        )
        err = np.log(np.abs(model)) - np.log(np.abs(z[sel]))
        factors.append((np.exp(np.sqrt(np.mean(err**2))), height / wavelength_m))
    return np.array(factors)


#: The fitted table, written beside this script as well as into the page.
#: The page must stay self-contained, so its copy is inlined rather than
#: imported; this file is the checkable original, and a test in
#: docs/tools asserts the two agree.
DATA = Path(__file__).resolve().parent / "coefficients.json"

#: The page marks the block this script owns.
PAGE = Path(__file__).resolve().parents[2] / "docs" / "random-wire.html"
BEGIN = "// BEGIN GENERATED COEFFICIENTS"
END = "// END GENERATED COEFFICIENTS"

#: Table names as the page spells them, parallel to TABLE_PARAMS.
JS_NAMES = ("alphaA", "kA", "alphaR", "vfR", "kR")


def render(table, soils, indent="    "):
    """The JavaScript block, without the markers that delimit it."""
    lines = [
        f"{indent}const MODEL_H_NODES = Object.freeze("
        f"[{', '.join(f'{n:g}' for n in NODES)}]);",
        f"{indent}const MODEL_COEFFS = Object.freeze({{",
    ]
    for si, soil in enumerate(soils):
        lines.append(f"{indent}  {soil}: Object.freeze({{")
        for pi, name in enumerate(JS_NAMES):
            values = ", ".join(f"{v:.4f}" for v in table[si, :, pi])
            lines.append(f"{indent}    {name}: [{values}],")
        lines.append(f"{indent}  }}),")
    lines.append(f"{indent}}});")
    return "\n".join(lines)


def write_data(table, soils, path=DATA):
    """Record the table as JSON, so the page's numbers have an original."""
    payload = {
        "note": "Generated by nec/random_wire/coefficients.py.  Do not edit.",
        "nodes_h_over_lambda": [float(n) for n in NODES],
        "vf_a": VF_A,
        "soils": {
            soil: {
                name: [round(float(v), 4) for v in table[si, :, pi]]
                for pi, name in enumerate(JS_NAMES)
            }
            for si, soil in enumerate(soils)
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


def patch_page(table, soils, path=PAGE):
    """Replace the marked block in the page.  Returns True if it changed."""
    text = path.read_text()
    pattern = re.compile(
        rf"(^[ \t]*{re.escape(BEGIN)}[^\n]*\n)(.*?)(^[ \t]*{re.escape(END)})",
        re.S | re.M,
    )
    match = pattern.search(text)
    if match is None:
        raise SystemExit(f"{path} has no {BEGIN} / {END} markers")
    replacement = f"{match.group(1)}{render(table, soils)}\n{match.group(3)}"
    updated = text[: match.start()] + replacement + text[match.end() :]
    if updated == text:
        return False
    path.write_text(updated)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="fitted coefficients for the page")
    parser.add_argument(
        "--write",
        action="store_true",
        help="patch docs/random-wire.html instead of printing the block",
    )
    args = parser.parse_args()

    d, z = load()
    soils = list(d["soil_names"])
    groups = fitted_groups(d, z)
    table = refine_table(build_table(groups, len(soils)), d, z, soils)

    err = tabulated_error(d, z, table)
    ok = err[:, 1] >= 0.05
    print("tabulated model, measured over the whole sweep")
    print(
        f"  all groups          : median x{np.median(err[:, 0]):.2f}  "
        f"90th x{np.percentile(err[:, 0], 90):.2f}  worst x{err[:, 0].max():.2f}"
    )
    print(
        f"  h/lambda >= 0.05    : median x{np.median(err[ok, 0]):.2f}  "
        f"90th x{np.percentile(err[ok, 0], 90):.2f}  worst x{err[ok, 0].max():.2f}"
    )
    print(
        f"  h/lambda <  0.05    : median x{np.median(err[~ok, 0]):.2f}  "
        f"worst x{err[~ok, 0].max():.2f}"
    )

    if args.write:
        write_data(table, soils)
        changed = patch_page(table, soils)
        print(f"\n{DATA}: written")
        print(f"{PAGE}: {'updated' if changed else 'already current'}")
    else:
        print("\n" + render(table, soils, indent=""))
        print("\n(run with --write to patch docs/random-wire.html)")
