"""Fit the two-line model to the sweep.

Structure comes from finding 7: the feedpoint is the antenna line and the
return line in series,

    Zin = Za(l) + Zr(h + ret)
    Za  = Z0a * coth((alpha_a + j*beta_a) * l)
    Zr  = kr * Z0r * coth((alpha_r + j*beta_r) * (h + ret))

with each Z0 from Schelkunoff.  The return gets its own scale `kr`
because it runs close to ground, where the image lowers the
characteristic impedance below the free-space thin-wire figure.

beta is fitted as a velocity factor rather than assumed, because measured
half-wave reactance is nowhere near zero (finding 3).

Residuals are taken on the complex logarithm.  |Zin| spans tens of ohms
to kilohms across a sweep, so an absolute residual would fit the peaks
and ignore everything else; log residual is relative in magnitude and
plain angular error in phase, which is what SWR actually cares about.
"""

import itertools

import numpy as np
from scipy.optimize import least_squares

from nec_model import C, WIRE_RADIUS_M

SWEEP = "sweep.npz"

#: Fitted parameters, in the order least_squares sees them.  The alphas
#: are nepers per wavelength, not per metre: fitted per metre they came
#: out proportional to frequency, which is just the statement that a wire
#: loses a fixed fraction per wavelength.  Per wavelength they are
#: comparable across bands, which is what the coefficient surface needs.
PARAM_NAMES = ("alpha_a_lam", "vf_a", "ka", "alpha_r_lam", "vf_r", "kr")

#: Start point and bounds.  alpha_r is capped well below the point where
#: coth saturates: past about 3 nepers per wavelength the return line
#: stops being a line at all and the fit uses it as a lumped constant,
#: which fits the data while meaning nothing.
#:
#: Velocity factors are capped at unity.  Left free they drifted to 1.018,
#: which is not a wave outrunning light but beta absorbing what the line
#: form omits: Z0 varies along a real wire where Schelkunoff's figure is
#: an average, the open end is capacitively loaded, and the structure
#: radiates.  Capping costs 0.5 percent of median accuracy and keeps the
#: parameter readable as what it claims to be.
#:
#: ka and kr scale each line's Schelkunoff Z0.  Schelkunoff's figure is
#: an average over an isolated wire in free space; over ground the image
#: lowers it, and both come out near 0.75, which is that effect.
INITIAL = (0.12, 0.98, 1.0, 0.5, 0.92, 0.7)
BOUNDS = ((1e-3, 0.5, 0.2, 1e-3, 0.4, 0.05), (3.0, 1.0, 5.0, 3.0, 1.0, 3.0))


def schelkunoff_z0(length_m, radius_m=WIRE_RADIUS_M):
    """Average characteristic impedance of a thin wire, ohms."""
    return 60.0 * (np.log(2.0 * length_m / radius_m) - 1.0)


def model_zin(params, length_m, total_return_m, wavelength_m):
    """Zin for the two-line model at the given lengths."""
    alpha_a_lam, vf_a, ka, alpha_r_lam, vf_r, kr = params
    alpha_a = alpha_a_lam / wavelength_m
    alpha_r = alpha_r_lam / wavelength_m
    beta_a = 2.0 * np.pi / (wavelength_m * vf_a)
    beta_r = 2.0 * np.pi / (wavelength_m * vf_r)
    za = (ka * schelkunoff_z0(length_m)) / np.tanh((alpha_a + 1j * beta_a) * length_m)
    zr = (kr * schelkunoff_z0(total_return_m)) / np.tanh(
        (alpha_r + 1j * beta_r) * total_return_m
    )
    return za + zr


def _residual(params, length_m, total_return_m, wavelength_m, z_nec):
    """Complex log residual, flattened to the real vector least_squares wants."""
    z = model_zin(params, length_m, total_return_m, wavelength_m)
    r = np.log(z) - np.log(z_nec)
    return np.concatenate([r.real, r.imag])


def fit_group(length_m, total_return_m, wavelength_m, z_nec):
    """Fit one (frequency, height, soil) group."""
    out = least_squares(
        _residual,
        INITIAL,
        bounds=BOUNDS,
        args=(length_m, total_return_m, wavelength_m, z_nec),
        max_nfev=4000,
    )
    # RMS of the log-magnitude residual, reported as a factor: exp(rms) is
    # the typical multiplicative error in |Z|.
    half = len(out.fun) // 2
    rms_log_mag = float(np.sqrt(np.mean(out.fun[:half] ** 2)))
    rms_phase = float(np.sqrt(np.mean(out.fun[half:] ** 2)))
    return out.x, np.exp(rms_log_mag), np.degrees(rms_phase)


def load():
    d = np.load(SWEEP, allow_pickle=False)
    return d, d["resistance"] + 1j * d["reactance"]


if __name__ == "__main__":
    d, z = load()
    soils = list(d["soil_names"])
    freqs = np.unique(d["freq_hz"])
    heights = np.unique(d["height_m"])

    print(
        f"{'f MHz':>7} {'h m':>5} {'soil':>8} "
        + " ".join(f"{n:>8}" for n in PARAM_NAMES)
        + f" {'x err':>7} {'deg':>6}"
    )
    results = []
    for freq, height, si in itertools.product(freqs, heights, range(len(soils))):
        sel = (d["freq_hz"] == freq) & (d["height_m"] == height) & (d["soil"] == si)
        wavelength_m = C / freq
        length_m = d["ratio"][sel] * wavelength_m
        total_return_m = height + d["return_m"][sel]
        params, factor, degrees = fit_group(
            length_m, total_return_m, wavelength_m, z[sel]
        )
        results.append((freq, height, si, params, factor, degrees))
        print(
            f"{freq / 1e6:7.2f} {height:5.0f} {soils[si]:>8} "
            + " ".join(f"{v:8.4f}" for v in params)
            + f" {factor:7.2f} {degrees:6.1f}"
        )

    factors = np.array([r[4] for r in results])
    print(
        f"\nmagnitude error factor: median {np.median(factors):.2f}, "
        f"90th pct {np.percentile(factors, 90):.2f}, worst {factors.max():.2f}"
    )
