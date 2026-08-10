"""Does a coupling term rescue the elevated-return case?

The two-line form fails as the return rises: x1.20 median at 15 cm,
x1.60 at 2 m, with each group given its own best coefficients.  The
reading is that `Za + Zr` assumes the two conductors do not see each
other, which holds while the return lies on the ground and its image
cancels the coupling, and stops holding once it is lifted clear.

The physically obvious repair is a mutual term:

    Zin = Za + Zr + 2 Zm

For two conductors carrying comparable current the mutual impedance
scales as the geometric mean of the two self impedances, so

    Zm = km * exp(-(h - rh) / (kd * lambda)) * sqrt(Za * Zr)

with the separation `h - rh` measured in wavelengths.  That has the two
limits the physics demands: full coupling as the conductors approach,
none as they separate.  `km` and `kd` are fitted alongside the rest, and
the five-parameter form is nested inside this one at `km = 0`, so the
comparison is fair.

Judged on the elevated-return groups, since that is what it exists to
fix.  Run against unified_fit.py, which is the same fit without it.
"""

import numpy as np
from scipy.optimize import least_squares

from fit import schelkunoff_z0
from nec_model import C, WIRE_RADIUS_M
from unified_fit import groups, load_unified

PARAM_NAMES = ("alpha_a_lam", "ka", "alpha_r_lam", "vf_r", "kr", "km", "kd")

#: vf_a stays pinned at unity, as everywhere else.
VF_A = 1.0

INITIAL = (0.12, 0.8, 0.5, 0.92, 0.75, 0.2, 0.5)
BOUNDS = (
    (1e-3, 0.2, 1e-3, 0.4, 0.05, 0.0, 0.02),
    (3.0, 5.0, 3.0, 1.0, 3.0, 2.0, 20.0),
)


def model_zin(
    params, length_m, total_return_m, wavelength_m, separation_m, radius_m=WIRE_RADIUS_M
):
    """The two lines plus a mutual term between them."""
    alpha_a_lam, ka, alpha_r_lam, vf_r, kr, km, kd = params
    gamma_a = alpha_a_lam / wavelength_m + 1j * 2.0 * np.pi / (wavelength_m * VF_A)
    gamma_r = alpha_r_lam / wavelength_m + 1j * 2.0 * np.pi / (wavelength_m * vf_r)
    za = ka * schelkunoff_z0(length_m, radius_m) / np.tanh(gamma_a * length_m)
    zr = (
        kr
        * schelkunoff_z0(total_return_m, radius_m)
        / np.tanh(gamma_r * total_return_m)
    )
    decay = np.exp(-(separation_m / wavelength_m) / kd)
    return za + zr + 2.0 * km * decay * np.sqrt(za * zr)


def _residual(params, length_m, total_return_m, wavelength_m, separation_m, z_nec):
    z = model_zin(params, length_m, total_return_m, wavelength_m, separation_m)
    r = np.log(z) - np.log(z_nec)
    return np.concatenate([r.real, r.imag])


def fit_group(length_m, total_return_m, wavelength_m, separation_m, z_nec):
    keep = z_nec.real > 0
    out = least_squares(
        _residual,
        INITIAL,
        bounds=BOUNDS,
        args=(
            length_m[keep],
            total_return_m[keep],
            wavelength_m,
            separation_m,
            z_nec[keep],
        ),
        max_nfev=8000,
    )
    half = len(out.fun) // 2
    return out.x, float(np.exp(np.sqrt(np.mean(out.fun[:half] ** 2))))


if __name__ == "__main__":
    d, z = load_unified()
    by_height = {}
    coefficients = []
    for si, freq, height, return_height, sel in groups(d):
        wavelength_m = C / freq
        params, factor = fit_group(
            d["ratio"][sel] * wavelength_m,
            height + d["return_m"][sel],
            wavelength_m,
            height - return_height,
            z[sel],
        )
        by_height.setdefault(return_height, []).append(factor)
        coefficients.append(params)

    print("with a coupling term, per-group error by return height")
    print(f"{'rh m':>7} {'median':>8} {'90th':>8} {'worst':>8}  {'without it':>12}")
    without = {0.01: 1.20, 0.05: 1.20, 0.15: 1.20, 0.5: 1.24, 1.0: 1.34, 2.0: 1.60}
    for rh in sorted(by_height):
        f = np.array(by_height[rh])
        print(
            f"{rh:7.2f} x{np.median(f):7.2f} x{np.percentile(f, 90):7.2f} "
            f"x{f.max():7.2f}  {'x' + format(without[rh], '.2f'):>12}"
        )

    coefficients = np.array(coefficients)
    print("\nfitted coupling parameters")
    for i, name in enumerate(PARAM_NAMES):
        col = coefficients[:, i]
        print(
            f"  {name:12} median {np.median(col):7.3f}  "
            f"min {col.min():7.3f}  max {col.max():7.3f}"
        )
    at_zero = (coefficients[:, 5] < 1e-3).mean()
    print(
        f"\n  km sits at zero in {100 * at_zero:.0f} percent of groups; "
        "at zero the term is absent and this is the old form"
    )
