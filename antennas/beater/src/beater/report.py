"""Text reports: the physical cut sheet and the frequency-sweep bandwidths.

Shared by the CLI and the plot page so both render identical numbers.
"""

from .design import (
    AR_TARGET_DB,
    BORESIGHT_THETA_DEG,
    MATCH_REACTANCE_WARN_OHMS,
    NEC_SENSE_TO_HAND,
    PHASING_SELF,
    REFLECTOR_NONE,
    REFLECTOR_RADIALS,
    VSWR_LIMIT,
    DesignResult,
    bandwidth_within,
    frequency_sweep,
    nearest_standard_coax,
    quarter_wave_match_z0,
    series_match_element,
    vswr,
)
from .geometry import loop_radius_m, wavelength_m

# Fraction of a wavelength in a quarter-wave phasing line.
QUARTER_WAVE = 0.25
# Display scale factors for series matching elements.
PF_PER_FARAD = 1.0e12
NH_PER_HENRY = 1.0e9


def loop_diameter_m(perimeter_m: float) -> float:
    return 2.0 * loop_radius_m(perimeter_m)


def _format_sense(result: DesignResult) -> str:
    """Achieved polarization sense, flagging any mismatch with the request."""
    achieved = NEC_SENSE_TO_HAND.get(result.sense)
    if achieved is None:
        return f"{result.sense} (requested {result.spec.sense})"
    if achieved == result.spec.sense:
        return achieved.upper()
    return f"{achieved.upper()} (requested {result.spec.sense.upper()} not achieved)"


def format_cut_sheet(result: DesignResult) -> str:
    """Render the tuned design as an ASCII cut sheet."""
    spec = result.spec
    wavelength = wavelength_m(spec.freq_mhz)
    z = result.z_in
    title = (
        f"Eggbeater cut sheet: {spec.label}" if spec.label else "Eggbeater cut sheet"
    )
    lines = [
        title,
        "=" * 40,
        f"Frequency           : {spec.freq_mhz:.4g} MHz",
        f"Wavelength          : {wavelength * 1000:.1f} mm",
        f"Conductor           : {spec.conductor.description}",
        f"  equivalent radius : {spec.conductor.equivalent_radius_mm:.4g} mm",
        f"Phasing             : {spec.phasing}",
        f"Reflector           : {spec.reflector}",
    ]
    if spec.reflector != REFLECTOR_NONE:
        spacing_mm = spec.reflector_spacing_wl * wavelength * 1000
        lines.append(
            f"  loop-center height: {spec.reflector_spacing_wl:.3g} wl "
            f"({spacing_mm:.1f} mm)"
        )
    if spec.reflector == REFLECTOR_RADIALS:
        radial_mm = spec.radial_length_wl * wavelength * 1000
        lines.append(
            f"  radials           : {spec.radial_count} x {radial_mm:.1f} mm, "
            f"{spec.radial_droop_deg:g} deg droop"
        )
    lines.append("-" * 40)

    if spec.phasing == PHASING_SELF:
        factor_a = result.base_factor * (1.0 + result.delta)
        factor_b = result.base_factor * (1.0 - result.delta)
        peri_a = factor_a * wavelength
        peri_b = factor_b * wavelength
        lines += [
            f"Detune (delta)      : {result.delta * 100:.2f} %",
            f"Large loop          : {peri_a * 1000:.1f} mm perimeter, "
            f"{loop_diameter_m(peri_a) * 1000:.1f} mm dia",
            f"Small loop          : {peri_b * 1000:.1f} mm perimeter, "
            f"{loop_diameter_m(peri_b) * 1000:.1f} mm dia",
            "Feed                : loops paralleled at a common feedpoint",
        ]
    else:
        peri = result.base_factor * wavelength
        line_len = QUARTER_WAVE * wavelength * spec.coax_vf
        lines += [
            f"Both loops          : {peri * 1000:.1f} mm perimeter, "
            f"{loop_diameter_m(peri) * 1000:.1f} mm dia",
            f"Phasing line        : {line_len * 1000:.1f} mm "
            f"(1/4 wave, VF {spec.coax_vf:g})",
            "Feed                : tee at junction; line in series with loop B",
        ]

    lines.append("-" * 40)
    z_label = "feedpoint Z" if spec.phasing == PHASING_SELF else "per-loop Z"
    lines += [
        f"Predicted {z_label:9}: {z.real:.1f} {z.imag:+.1f}j ohms",
        f"VSWR (50 ohm)       : {vswr(z):.2f}",
        f"Loop current phase  : {result.phase_diff_deg:+.1f} deg (target +/-90)",
        f"Polarization sense  : {_format_sense(result)}",
        f"Axial ratio (boresight): {result.ar_boresight_db:.2f} dB "
        f"(<= {int(BORESIGHT_THETA_DEG)} deg from zenith)",
        f"Axial ratio (gain peak): {result.ar_peak_db:.2f} dB",
    ]

    lines.append("-" * 40)
    z0 = quarter_wave_match_z0(z)
    match_len = QUARTER_WAVE * wavelength * spec.match_vf
    lines.append("Match to 50 ohm:")
    if abs(z.imag) > MATCH_REACTANCE_WARN_OHMS:
        kind, value = series_match_element(z, spec.freq_mhz)
        if kind == "capacitor":
            sized = f"{value * PF_PER_FARAD:.1f} pF"
        else:
            sized = f"{value * NH_PER_HENRY:.0f} nH"
        lines.append(f"  series {kind:9}  : {sized} to cancel {z.imag:+.0f}j ohms")
    lines += [
        f"  1/4-wave Z0       : {z0:.1f} ohms "
        f"(nearest standard {nearest_standard_coax(z0):.0f} ohm)",
        f"  1/4-wave length   : {match_len * 1000:.1f} mm (VF {spec.match_vf:g})",
    ]
    return "\n".join(lines) + "\n"


def _band_line(label: str, band: tuple[float, float] | None, center: float) -> str:
    """One bandwidth line, or a not-met note when the band is empty."""
    if band is None:
        return f"  {label:18}: not met at the design frequency"
    low, high = band
    width = high - low
    return (
        f"  {label:18}: {low:.2f} - {high:.2f} MHz "
        f"({width:.2f} MHz, {100 * width / center:.1f} %)"
    )


def format_bandwidth(result: DesignResult) -> str:
    """Run a frequency sweep and render the VSWR and axial-ratio bandwidths."""
    sweep = frequency_sweep(result)
    center = result.spec.freq_mhz
    vswr_band = bandwidth_within([(p.freq_mhz, p.vswr) for p in sweep], VSWR_LIMIT)
    ar_band = bandwidth_within([(p.freq_mhz, p.ar_db) for p in sweep], AR_TARGET_DB)
    lines = [
        "-" * 40,
        f"Frequency sweep ({len(sweep)} points):",
        _band_line(f"{VSWR_LIMIT:g}:1 VSWR", vswr_band, center),
        _band_line(f"{AR_TARGET_DB:g} dB axial ratio", ar_band, center),
    ]
    return "\n".join(lines) + "\n"
