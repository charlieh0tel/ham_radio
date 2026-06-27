"""Command-line interface: tune eggbeater designs from a JSON spec."""

import argparse
import sys
from dataclasses import replace

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
    DesignSpec,
    bandwidth_within,
    design,
    frequency_sweep,
    nearest_standard_coax,
    optimize_reflector,
    quarter_wave_match_z0,
    series_match_element,
    vswr,
)
from .geometry import loop_radius_m, wavelength_m
from .plot import render_artifact
from .spec import specs_from_json

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beater",
        description="Tune eggbeater antenna designs from a JSON spec.",
    )
    parser.add_argument(
        "spec",
        nargs="?",
        default="-",
        help="path to a JSON spec (one design or a list); '-' or omitted reads stdin",
    )
    parser.add_argument(
        "--optimize-reflector",
        action="store_true",
        help="grid-search reflector spacing and droop for the best match",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="sweep frequency and report the 2:1 VSWR and 3 dB axial-ratio bands",
    )
    parser.add_argument(
        "--deck",
        help="write the tuned NEC deck to this path (single-design specs only)",
    )
    parser.add_argument(
        "--plot",
        help="write a performance plot page (HTML) for the design(s) to this path",
    )
    parser.add_argument("--nec2c", default="nec2c", help="nec2c executable")
    return parser


def load_specs(path: str) -> list[DesignSpec]:
    """Read specs from a file path, or stdin when path is '-'."""
    text = sys.stdin.read() if path == "-" else open(path).read()
    return specs_from_json(text)


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    specs = [replace(spec, nec2c=args.nec2c) for spec in load_specs(args.spec)]
    if args.deck and len(specs) > 1:
        parser.error("--deck requires a single-design spec")

    results = []
    for index, spec in enumerate(specs):
        if args.optimize_reflector and spec.reflector == REFLECTOR_NONE:
            parser.error("--optimize-reflector requires a reflector")
        result = optimize_reflector(spec) if args.optimize_reflector else design(spec)
        results.append(result)
        if index:
            print()
        print(format_cut_sheet(result), end="")
        if args.sweep:
            print(format_bandwidth(result), end="")
        if args.deck:
            with open(args.deck, "w") as handle:
                handle.write(result.deck)
            print(f"Wrote NEC deck to {args.deck}")

    if args.plot:
        with open(args.plot, "w") as handle:
            handle.write(render_artifact(results))
        print(f"Wrote plot page to {args.plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
