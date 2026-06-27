"""Command-line interface: tune an eggbeater and print a physical cut sheet."""

import argparse

from .conductor import Conductor, bar_conductor, round_conductor, strip_conductor
from .design import (
    BORESIGHT_THETA_DEG,
    MATCH_REACTANCE_WARN_OHMS,
    PHASING_LINE,
    PHASING_SELF,
    REFLECTOR_GROUND,
    REFLECTOR_NONE,
    DesignResult,
    DesignSpec,
    design,
    nearest_standard_coax,
    quarter_wave_match_z0,
    series_match_element,
    vswr,
)
from .geometry import DEFAULT_SEGMENTS, loop_radius_m, wavelength_m

# Fraction of a wavelength in a quarter-wave phasing line.
QUARTER_WAVE = 0.25
# Display scale factors for series matching elements.
PF_PER_FARAD = 1.0e12
NH_PER_HENRY = 1.0e9


def parse_conductor(spec: str) -> Conductor:
    """Parse a conductor spec string.

    Forms: 'round:<dia_mm>', 'strip:<width_mm>', 'bar:<width_mm>x<thick_mm>'.
    All dimensions are millimetres.
    """
    kind, _, rest = spec.partition(":")
    if not rest:
        raise argparse.ArgumentTypeError(f"missing dimensions in conductor '{spec}'")
    try:
        if kind == "round":
            return round_conductor(float(rest))
        if kind == "strip":
            return strip_conductor(float(rest))
        if kind == "bar":
            width, _, thick = rest.partition("x")
            return bar_conductor(float(width), float(thick))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"bad conductor '{spec}': {exc}") from exc
    raise argparse.ArgumentTypeError(
        f"unknown conductor kind '{kind}' (use round, strip, or bar)"
    )


def loop_diameter_m(perimeter_m: float) -> float:
    return 2.0 * loop_radius_m(perimeter_m)


def format_cut_sheet(result: DesignResult) -> str:
    """Render the tuned design as an ASCII cut sheet."""
    spec = result.spec
    wavelength = wavelength_m(spec.freq_mhz)
    z = result.z_in
    lines = [
        "Eggbeater antenna cut sheet",
        "=" * 40,
        f"Frequency           : {spec.freq_mhz:.4g} MHz",
        f"Wavelength          : {wavelength * 1000:.1f} mm",
        f"Conductor           : {spec.conductor.description}",
        f"  equivalent radius : {spec.conductor.equivalent_radius_mm:.4g} mm",
        f"Phasing             : {spec.phasing}",
        f"Reflector           : {spec.reflector}",
    ]
    if spec.reflector == REFLECTOR_GROUND:
        spacing_mm = spec.reflector_spacing_wl * wavelength * 1000
        lines.append(
            f"  loop-center height: {spec.reflector_spacing_wl:.3g} wl "
            f"({spacing_mm:.1f} mm)"
        )
    lines.append("-" * 40)

    if spec.phasing == PHASING_SELF:
        factor_a = result.base_factor * (1.0 + result.delta)
        factor_b = result.base_factor * (1.0 - result.delta)
        peri_a = factor_a * wavelength
        peri_b = factor_b * wavelength
        lines += [
            f"Detune (delta)      : {result.delta * 100:.2f} %",
            f"Loop A (large)      : {peri_a * 1000:.1f} mm perimeter, "
            f"{loop_diameter_m(peri_a) * 1000:.1f} mm dia",
            f"Loop B (small)      : {peri_b * 1000:.1f} mm perimeter, "
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
        f"Polarization sense  : {result.sense}",
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
        description="Generate and nec2c-tune eggbeater antenna dimensions.",
    )
    parser.add_argument("--freq", type=float, required=True, help="frequency in MHz")
    parser.add_argument(
        "--conductor",
        type=parse_conductor,
        required=True,
        help="round:<dia_mm> | strip:<width_mm> | bar:<width_mm>x<thick_mm>",
    )
    parser.add_argument(
        "--phasing",
        choices=(PHASING_SELF, PHASING_LINE),
        default=PHASING_SELF,
    )
    parser.add_argument(
        "--reflector",
        choices=(REFLECTOR_NONE, REFLECTOR_GROUND),
        default=REFLECTOR_NONE,
    )
    parser.add_argument(
        "--reflector-spacing",
        type=float,
        default=0.25,
        help="loop-center height above ground in wavelengths",
    )
    parser.add_argument(
        "--coax-vf",
        type=float,
        default=0.66,
        help="phasing-line coax velocity factor (line phasing)",
    )
    parser.add_argument(
        "--match-vf",
        type=float,
        default=0.66,
        help="matching-section coax velocity factor",
    )
    parser.add_argument("--segments", type=int, default=DEFAULT_SEGMENTS)
    parser.add_argument("--nec2c", default="nec2c", help="nec2c executable")
    parser.add_argument("--deck", help="write the tuned NEC deck to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.freq <= 0.0:
        build_parser().error("--freq must be positive")
    spec = DesignSpec(
        freq_mhz=args.freq,
        conductor=args.conductor,
        phasing=args.phasing,
        reflector=args.reflector,
        reflector_spacing_wl=args.reflector_spacing,
        coax_vf=args.coax_vf,
        match_vf=args.match_vf,
        segments=args.segments,
        nec2c=args.nec2c,
    )
    result = design(spec)
    print(format_cut_sheet(result), end="")
    if args.deck:
        with open(args.deck, "w") as handle:
            handle.write(result.deck)
        print(f"Wrote NEC deck to {args.deck}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
