"""Does an end-effect term earn its place?  (No.)

The five-parameter form leaves vf_a pressed against its cap, and a
rail-pinned parameter usually means the model is missing something.  Two
candidates on the antenna side:

  ka  a scale on Z0a.  Schelkunoff gives an *average* characteristic
      impedance, but Z0 varies along a real wire, so the average may be
      systematically off.
  be  a normalised susceptance terminating the open end, standing for the
      capacitive loading of a real wire end.

Terminating a line of characteristic impedance Z0 in a shunt susceptance
`be` normalised to Y0 = 1/Z0 gives

    Zin = Z0 * (be*tanh(gamma l) - j) / (be - j*tanh(gamma l))

which reduces to Z0 coth(gamma l) as be goes to zero, so the shipped form
is nested inside this one and the comparison is fair.

`ka` earned its place and is in fit.py.  `be` did not: it fits to zero in
every group.  This script is kept so that rejection stays reproducible --
it was originally run and deleted, which left a documented negative
result with no instrument behind it.
"""

import itertools

import numpy as np
from scipy.optimize import least_squares

from fit import load, schelkunoff_z0
from nec_model import C, WIRE_RADIUS_M

PARAM_NAMES = ("alpha_a_lam", "vf_a", "ka", "be", "alpha_r_lam", "vf_r", "kr")

#: vf_a is left free above unity here on purpose: the question is whether
#: the end-effect term pulls it off the rail by itself.
INITIAL = (0.12, 0.98, 1.0, 0.0, 0.5, 0.92, 0.7)
BOUNDS = (
    (1e-3, 0.5, 0.2, 0.0, 1e-3, 0.4, 0.05),
    (3.0, 1.15, 5.0, 5.0, 3.0, 1.15, 3.0),
)


def model_zin(params, length_m, total_return_m, wavelength_m, radius_m=WIRE_RADIUS_M):
    """Antenna line with a terminated open end, plus the return line."""
    alpha_a_lam, vf_a, ka, be, alpha_r_lam, vf_r, kr = params
    gamma_a = alpha_a_lam / wavelength_m + 1j * 2.0 * np.pi / (wavelength_m * vf_a)
    gamma_r = alpha_r_lam / wavelength_m + 1j * 2.0 * np.pi / (wavelength_m * vf_r)
    z0a = ka * schelkunoff_z0(length_m, radius_m)
    t = np.tanh(gamma_a * length_m)
    za = z0a * (be * t - 1j) / (be - 1j * t)
    zr = (
        kr
        * schelkunoff_z0(total_return_m, radius_m)
        / np.tanh(gamma_r * total_return_m)
    )
    return za + zr


def _residual(params, length_m, total_return_m, wavelength_m, z_nec):
    z = model_zin(params, length_m, total_return_m, wavelength_m)
    magnitude = np.log(np.abs(z)) - np.log(np.abs(z_nec))
    phase = np.angle(z) - np.angle(z_nec)
    phase = (phase + np.pi) % (2.0 * np.pi) - np.pi
    return np.concatenate([magnitude, phase])


def fit_group(length_m, total_return_m, wavelength_m, z_nec):
    out = least_squares(
        _residual,
        INITIAL,
        bounds=BOUNDS,
        args=(length_m, total_return_m, wavelength_m, z_nec),
        max_nfev=8000,
    )
    half = len(out.fun) // 2
    return out.x, float(np.exp(np.sqrt(np.mean(out.fun[:half] ** 2))))


if __name__ == "__main__":
    d, z = load()
    rows, factors = [], []
    for freq, height, si in itertools.product(
        np.unique(d["freq_hz"]), np.unique(d["height_m"]), range(len(d["soil_names"]))
    ):
        sel = (d["freq_hz"] == freq) & (d["height_m"] == height) & (d["soil"] == si)
        wavelength_m = C / freq
        params, factor = fit_group(
            d["ratio"][sel] * wavelength_m,
            height + d["return_m"][sel],
            wavelength_m,
            z[sel],
        )
        rows.append(params)
        factors.append(factor)

    rows = np.array(rows)
    factors = np.array(factors)
    print(f"seven-parameter fit over {len(rows)} groups")
    print(
        f"  magnitude error: median x{np.median(factors):.3f}  "
        f"90th x{np.percentile(factors, 90):.3f}  worst x{factors.max():.3f}"
    )
    for i, name in enumerate(PARAM_NAMES):
        col = rows[:, i]
        print(
            f"  {name:12} median {np.median(col):7.4f}  "
            f"min {col.min():7.4f}  max {col.max():7.4f}"
        )

    be = rows[:, 3]
    print(
        f"\nend-effect susceptance is zero in "
        f"{100 * (be < 1e-3).mean():.0f} percent of groups, largest "
        f"{be.max():.4f}"
    )
    print("It buys nothing, so fit.py carries ka and not be.")
