"""Does a second table dimension for counterpoise height pay for itself?

Three proxies have pointed three ways.  Median coefficients looked smooth
and monotonic, suggesting a one-dimensional correction would do.  A
log-linear R2 said no index explains `alpha_r` well.  Per-slice
smoothness said the surface is rough -- monotonic in only 12 of 32
slices, adjacent nodes a factor of 1.69 apart.

None of those is the question.  `alpha_r`, `vf_r` and `kr` trade off
against one another, so the fit can wander in a coefficient while `|Z|`
stays put, and a table is judged on the impedance it delivers rather than
on the tidiness of its contents.  This measures that directly, the same
way `coefficients.py` measures the shipped table.

Three tables over the same sweep:

  1-D          indexed on h/lambda alone, as today, fitted to data that
               spans every counterpoise height.  This is the cost of
               ignoring the axis.
  2-D, z/lam   a second index on counterpoise height in wavelengths,
               which is what sets a line's coupling to lossy ground and
               is the same quantity h/lambda already is for the antenna.
  2-D, z/h     a second index on counterpoise height as a fraction of
               wire height, which is how the sweep stepped it.

Refinement is deliberately left out of all three.  `coefficients.py`
refines the shipped table jointly and that would help each of these, but
unequally and at some cost in time; comparing them unrefined keeps the
comparison honest about what the extra dimension itself buys.

    uv run python table2d.py
"""

import itertools

import numpy as np

from coefficients import MIN_H_OVER_LAMBDA, NODES, SOURCE_INDEX, TABLE_PARAMS, VF_A
from fit import fit_group, model_zin
from nec_model import C

SWEEP = "nec4_return_height_sweep.npz"

#: Nodes for the counterpoise axis, one per decade-ish over the span the
#: sweep covers.  Held flat outside, as the h/lambda axis is.
Z_LAM_NODES = np.array([1e-4, 1e-3, 4e-3, 1.5e-2, 6e-2])
Z_H_NODES = np.array([0.001, 0.02, 0.05, 0.1, 0.25, 0.5])

#: Width of the weighting kernel, in decades, matching build_table.
KERNEL_DECADES = 0.5


def fitted(data):
    """Per-group fits, with the coordinates each candidate index needs."""
    out = []
    for si, freq_hz, height_m, step in itertools.product(
        range(len(data["soil_names"])),
        np.unique(data["freq_hz"]),
        np.unique(data["height_m"]),
        np.unique(data["step"]),
    ):
        sel = (
            (data["freq_hz"] == freq_hz)
            & (data["height_m"] == height_m)
            & (data["soil"] == si)
            & (data["step"] == step)
            & np.isfinite(data["resistance"])
        )
        if sel.sum() < 20:
            continue
        wavelength_m = C / freq_hz
        z_m = float(np.unique(data["return_height_m"][sel])[0])
        total_return_m = (height_m - data["return_height_m"][sel]) + data["return_m"][
            sel
        ]
        params, _, _ = fit_group(
            data["ratio"][sel] * wavelength_m,
            total_return_m,
            wavelength_m,
            data["resistance"][sel] + 1j * data["reactance"][sel],
        )
        out.append(
            {
                "soil": si,
                "freq_hz": freq_hz,
                "height_m": height_m,
                "step": step,
                "h_lam": height_m / wavelength_m,
                "z_lam": z_m / wavelength_m,
                "z_h": z_m / height_m,
                "params": params,
            }
        )
    return out


def weighted_median(values, weights):
    """The value at which half the weight lies below."""
    order = np.argsort(values)
    cumulative = np.cumsum(weights[order])
    return values[order][np.searchsorted(cumulative, cumulative[-1] / 2.0)]


def build(groups, n_soils, second=None, second_nodes=None):
    """A table over h/lambda, and optionally over a second coordinate."""
    shape = (n_soils, len(NODES), len(TABLE_PARAMS))
    if second is not None:
        shape = (n_soils, len(NODES), len(second_nodes), len(TABLE_PARAMS))
    table = np.zeros(shape)
    for si in range(n_soils):
        mine = [g for g in groups if g["soil"] == si]
        h_lam = np.array([g["h_lam"] for g in mine])
        params = np.array([g["params"] for g in mine])
        y = np.array([g[second] for g in mine]) if second is not None else None
        for ni, node in enumerate(NODES):
            w_h = np.exp(-((np.log10(h_lam / node) / KERNEL_DECADES) ** 2))
            if second is None:
                for pi, source in enumerate(SOURCE_INDEX):
                    table[si, ni, pi] = weighted_median(params[:, source], w_h)
                continue
            for mi, ynode in enumerate(second_nodes):
                w = w_h * np.exp(
                    -((np.log10(np.clip(y, 1e-9, None) / ynode) / KERNEL_DECADES) ** 2)
                )
                if w.sum() <= 0:
                    w = w_h
                for pi, source in enumerate(SOURCE_INDEX):
                    table[si, ni, mi, pi] = weighted_median(params[:, source], w)
    return table


def look_up(table, si, h_lam, second_nodes=None, y=None):
    """Linear in log10 along each axis, clamped at both ends."""
    x = np.log10(np.clip(h_lam, NODES[0], NODES[-1]))
    xs = np.log10(NODES)
    if second_nodes is None:
        return np.array(
            [np.interp(x, xs, table[si, :, pi]) for pi in range(len(TABLE_PARAMS))]
        )
    v = np.log10(np.clip(y, second_nodes[0], second_nodes[-1]))
    vs = np.log10(second_nodes)
    return np.array(
        [
            np.interp(
                x,
                xs,
                [np.interp(v, vs, table[si, ni, :, pi]) for ni in range(len(NODES))],
            )
            for pi in range(len(TABLE_PARAMS))
        ]
    )


def error(data, table, second=None, second_nodes=None):
    """Tabulated error over the sweep, as coefficients.py measures it."""
    factors = []
    for si, freq_hz, height_m, step in itertools.product(
        range(len(data["soil_names"])),
        np.unique(data["freq_hz"]),
        np.unique(data["height_m"]),
        np.unique(data["step"]),
    ):
        sel = (
            (data["freq_hz"] == freq_hz)
            & (data["height_m"] == height_m)
            & (data["soil"] == si)
            & (data["step"] == step)
            & np.isfinite(data["resistance"])
        )
        if not sel.sum():
            continue
        wavelength_m = C / freq_hz
        z_m = float(np.unique(data["return_height_m"][sel])[0])
        y = (z_m / wavelength_m) if second == "z_lam" else (z_m / height_m)
        alpha_a, ka, alpha_r, vf_r, kr = look_up(
            table, si, height_m / wavelength_m, second_nodes, y
        )
        total_return_m = (height_m - data["return_height_m"][sel]) + data["return_m"][
            sel
        ]
        model = model_zin(
            (alpha_a, VF_A, ka, alpha_r, vf_r, kr),
            data["ratio"][sel] * wavelength_m,
            total_return_m,
            wavelength_m,
        )
        err = np.log(np.abs(model)) - np.log(
            np.abs(data["resistance"][sel] + 1j * data["reactance"][sel])
        )
        factors.append((np.exp(np.sqrt(np.mean(err**2))), height_m / wavelength_m))
    return np.array(factors)


def report(name, factors):
    inside = factors[factors[:, 1] >= MIN_H_OVER_LAMBDA][:, 0]
    all_of = factors[:, 0]
    print(
        f"  {name:<16} all median x{np.median(all_of):.2f} 90th "
        f"x{np.percentile(all_of, 90):.2f}   h/lam>=0.05 median "
        f"x{np.median(inside):.2f} 90th x{np.percentile(inside, 90):.2f} "
        f"worst x{inside.max():.2f}"
    )


if __name__ == "__main__":
    data = np.load(SWEEP, allow_pickle=False)
    groups = fitted(data)
    n_soils = len(data["soil_names"])
    print(f"{len(groups)} groups fitted from {SWEEP}\n")

    print("tabulated error, unrefined:")
    report("1-D h/lambda", error(data, build(groups, n_soils)))
    report(
        "2-D with z/lambda",
        error(
            data,
            build(groups, n_soils, "z_lam", Z_LAM_NODES),
            "z_lam",
            Z_LAM_NODES,
        ),
    )
    report(
        "2-D with z/h",
        error(data, build(groups, n_soils, "z_h", Z_H_NODES), "z_h", Z_H_NODES),
    )
    print(
        "\nThe shipped 1-D table, fitted and measured on a fixed 5 cm return,\n"
        "reads x1.25 median and x1.32 at the 90th for h/lambda >= 0.05."
    )
