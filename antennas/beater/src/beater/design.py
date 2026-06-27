"""Design orchestration: build geometry, drive nec2c, tune resonance and phase.

A single model serves both phasing schemes.  Both loops are driven by voltage
sources; the scheme only changes how the two sources relate:

  self  - equal feed phase, loop perimeters detuned by +/- delta so the two loop
          currents fall ~90 deg apart (the classic large-loop/small-loop trick).
  line  - equal resonant loops, feed phases 0 and -90 deg, modelling an ideal
          quarter-wave phasing line between them.
"""

import cmath
import math
from dataclasses import dataclass

from .conductor import Conductor
from .geometry import loop_radius_m, make_eggbeater, wavelength_m
from .nec import (
    DEFAULT_NEC2C,
    NecResult,
    RadiationGrid,
    Source,
    build_deck,
    run_nec,
)

PHASING_SELF = "self"
PHASING_LINE = "line"
REFLECTOR_NONE = "none"
REFLECTOR_GROUND = "ground"

# Feed phase of loop B for the quarter-wave-line scheme.
LINE_PHASE_DEG = -90.0
REFERENCE_IMPEDANCE_OHMS = 50.0
# Common coax characteristic impedances suggested for the matching section.
STANDARD_COAX_OHMS = (50.0, 75.0, 93.0)
# Residual feedpoint reactance above which a series tuning note is warranted.
MATCH_REACTANCE_WARN_OHMS = 10.0

# Upper-hemisphere sampling grid: theta 0..80 deg, phi 0..90 deg.
DEFAULT_GRID = RadiationGrid(
    ntheta=9, nphi=7, theta0=0.0, phi0=0.0, dtheta=10.0, dphi=15.0
)

# Bounds and convergence controls for the solvers.
FACTOR_BOUNDS = (0.70, 1.40)
DELTA_BOUNDS = (0.0, 0.15)
SOLVER_MAX_ITERATIONS = 40
REACTANCE_TOLERANCE_OHMS = 0.5
# Golden-section ratio and absolute delta tolerance for the AR minimization.
GOLDEN_RATIO = (math.sqrt(5.0) - 1.0) / 2.0
DELTA_TOLERANCE = 1e-3
# Axial ratio is optimized and reported over the high-elevation coverage cone,
# theta <= BORESIGHT_THETA_DEG from zenith (the region that matters for the
# satellite use case), rather than at the raw gain peak.
BORESIGHT_THETA_DEG = 30.0
# Total gains at or below this level mark pattern nulls and are ignored.
NULL_GAIN_DB = -100.0


@dataclass(frozen=True)
class DesignSpec:
    """Inputs that define a design problem.

    Fields:
        freq_mhz: design frequency.
        conductor: conductor cross-section.
        phasing: PHASING_SELF or PHASING_LINE.
        reflector: REFLECTOR_NONE or REFLECTOR_GROUND.
        reflector_spacing_wl: loop-centre height above ground, wavelengths.
        coax_vf: velocity factor of the phasing-line coax (line scheme).
        match_vf: velocity factor of the matching-section coax.
        segments: polygon sides per loop.
        nec2c: nec2c executable name or path.
    """

    freq_mhz: float
    conductor: Conductor
    phasing: str
    reflector: str
    reflector_spacing_wl: float
    coax_vf: float
    match_vf: float
    segments: int
    nec2c: str = DEFAULT_NEC2C


@dataclass(frozen=True)
class DesignResult:
    """Tuned design and its predicted performance.

    Fields:
        spec: the originating DesignSpec.
        base_factor: resonant perimeter as a multiple of wavelength.
        delta: self-phasing detune fraction (0 for the line scheme).
        z_in: predicted feedpoint impedance (combined for self phasing,
            per-loop for line phasing).
        phase_diff_deg: loop current phase difference.
        sense: polarization sense reported at the pattern peak.
        ar_boresight_db: mean axial ratio over the high-elevation coverage cone
            (theta <= BORESIGHT_THETA_DEG), dB; 0 is perfect circular.
        ar_peak_db: axial ratio at the pattern peak (dB).
        deck: the tuned NEC deck text.
    """

    spec: DesignSpec
    base_factor: float
    delta: float
    z_in: complex
    phase_diff_deg: float
    sense: str
    ar_boresight_db: float
    ar_peak_db: float
    deck: str


def _center_z_m(spec: DesignSpec, wavelength: float, perimeter_m: float) -> float:
    if spec.reflector == REFLECTOR_GROUND:
        return spec.reflector_spacing_wl * wavelength
    # In free space the absolute height is irrelevant; keep the loop above the
    # origin for readable coordinates.
    return loop_radius_m(perimeter_m)


def _comment_lines(spec: DesignSpec) -> list[str]:
    return [
        "Eggbeater antenna (crossed full-wave loops)",
        f"freq {spec.freq_mhz:g} MHz, phasing {spec.phasing}, "
        f"reflector {spec.reflector}",
        f"conductor: {spec.conductor.description}, "
        f"equiv radius {spec.conductor.equivalent_radius_mm:.4g} mm",
    ]


def _sources(spec: DesignSpec, egg, phase_b_deg: float) -> tuple[Source, ...]:
    phase_b = math.radians(phase_b_deg)
    return (
        Source(egg.loop_a.feed_tag, egg.loop_a.feed_segment, 1.0, 0.0),
        Source(
            egg.loop_b.feed_tag,
            egg.loop_b.feed_segment,
            math.cos(phase_b),
            math.sin(phase_b),
        ),
    )


def analyze(
    spec: DesignSpec,
    factor_a: float,
    factor_b: float,
    phase_b_deg: float,
) -> tuple[NecResult, str]:
    """Run nec2c once for the given perimeters and feed phase.

    Returns the parsed result and the deck text.  Sources are ordered loop A
    then loop B, matching nec2c's reporting order.
    """
    wavelength = wavelength_m(spec.freq_mhz)
    perimeter_a = factor_a * wavelength
    perimeter_b = factor_b * wavelength
    center_z = _center_z_m(spec, wavelength, perimeter_a)
    egg = make_eggbeater(
        perimeter_a,
        perimeter_b,
        center_z,
        spec.conductor.equivalent_radius_m,
        spec.segments,
    )
    sources = _sources(spec, egg, phase_b_deg)
    deck = build_deck(
        _comment_lines(spec),
        egg.wires,
        sources,
        ground=spec.reflector == REFLECTOR_GROUND,
        freq_mhz=spec.freq_mhz,
        grid=DEFAULT_GRID,
    )
    return run_nec(deck, spec.nec2c), deck


def _secant(func, x0: float, x1: float, bounds, tolerance: float) -> float:
    """Bounded secant root find for a scalar function."""
    low, high = bounds
    f0 = func(x0)
    f1 = func(x1)
    for _ in range(SOLVER_MAX_ITERATIONS):
        if abs(f1) <= tolerance:
            return x1
        denom = f1 - f0
        if denom == 0.0:
            return x1
        x2 = x1 - f1 * (x1 - x0) / denom
        x2 = min(max(x2, low), high)
        x0, f0 = x1, f1
        x1, f1 = x2, func(x2)
    return x1


def _resonant_factor(spec: DesignSpec) -> float:
    """Find the perimeter factor giving zero loop reactance (delta = 0)."""

    def reactance(factor: float) -> float:
        result, _ = analyze(spec, factor, factor, 0.0)
        return result.sources[0].z_imag

    return _secant(reactance, 1.0, 1.05, FACTOR_BOUNDS, REACTANCE_TOLERANCE_OHMS)


def _phase_difference(result: NecResult) -> float:
    return result.sources[0].current_phase_deg - result.sources[1].current_phase_deg


def _axial_ratio_db(axial_ratio: float) -> float:
    """Convert NEC minor/major axial ratio to dB (0 dB = perfect circular)."""
    if axial_ratio <= 0.0:
        return math.inf
    return -20.0 * math.log10(axial_ratio)


def _boresight_ar_db(result: NecResult) -> float:
    """Mean axial ratio (dB) over the high-elevation coverage cone.

    A single detune knob cannot force both equal current magnitude and a 90 deg
    phase split, so axial ratio (which captures both) is the proper objective.
    """
    cone = [
        p
        for p in result.pattern
        if p.theta_deg <= BORESIGHT_THETA_DEG and p.total_gain_db > NULL_GAIN_DB
    ]
    if not cone:
        return math.inf
    return sum(_axial_ratio_db(p.axial_ratio) for p in cone) / len(cone)


def _self_phase_delta(spec: DesignSpec, base_factor: float) -> float:
    """Detune fraction minimizing boresight axial ratio (golden-section search)."""

    def cost(delta: float) -> float:
        result, _ = analyze(
            spec, base_factor * (1.0 + delta), base_factor * (1.0 - delta), 0.0
        )
        return _boresight_ar_db(result)

    low, high = DELTA_BOUNDS
    x1 = high - GOLDEN_RATIO * (high - low)
    x2 = low + GOLDEN_RATIO * (high - low)
    f1, f2 = cost(x1), cost(x2)
    while high - low > DELTA_TOLERANCE:
        if f1 < f2:
            high, x2, f2 = x2, x1, f1
            x1 = high - GOLDEN_RATIO * (high - low)
            f1 = cost(x1)
        else:
            low, x1, f1 = x1, x2, f2
            x2 = low + GOLDEN_RATIO * (high - low)
            f2 = cost(x2)
    return (low + high) / 2.0


def _polarization_summary(result: NecResult) -> tuple[float, float, str]:
    """Boresight axial ratio, peak axial ratio, and peak sense (all dB)."""
    usable = [p for p in result.pattern if p.total_gain_db > NULL_GAIN_DB]
    if not usable:
        return math.inf, math.inf, "UNKNOWN"
    peak = max(usable, key=lambda p: p.total_gain_db)
    return _boresight_ar_db(result), _axial_ratio_db(peak.axial_ratio), peak.sense


def vswr(z: complex, reference: float = REFERENCE_IMPEDANCE_OHMS) -> float:
    """Voltage standing wave ratio of impedance z against a reference."""
    gamma = abs((z - reference) / (z + reference))
    if gamma >= 1.0:
        return math.inf
    return (1.0 + gamma) / (1.0 - gamma)


def quarter_wave_match_z0(
    z: complex, reference: float = REFERENCE_IMPEDANCE_OHMS
) -> float:
    """Characteristic impedance of a quarter-wave transformer.

    Matches the resistive part of z to the reference; any residual reactance
    must be tuned out separately.
    """
    return math.sqrt(reference * z.real)


def nearest_standard_coax(z0: float) -> float:
    """Closest common coax characteristic impedance to z0."""
    return min(STANDARD_COAX_OHMS, key=lambda c: abs(c - z0))


def design(spec: DesignSpec) -> DesignResult:
    """Tune an eggbeater to the spec and return the result."""
    base_factor = _resonant_factor(spec)
    if spec.phasing == PHASING_SELF:
        delta = _self_phase_delta(spec, base_factor)
        factor_a = base_factor * (1.0 + delta)
        factor_b = base_factor * (1.0 - delta)
        phase_b = 0.0
    else:
        delta = 0.0
        factor_a = base_factor
        factor_b = base_factor
        phase_b = LINE_PHASE_DEG
    result, deck = analyze(spec, factor_a, factor_b, phase_b)
    src_a, src_b = result.sources[0], result.sources[1]
    if spec.phasing == PHASING_SELF:
        # Loops are paralleled across a common feed voltage of 1 V.
        total_current = complex(src_a.i_real, src_a.i_imag) + complex(
            src_b.i_real, src_b.i_imag
        )
        z_in = 1.0 / total_current if total_current != 0 else cmath.inf
    else:
        # Each loop presents its own driving impedance; the tee plus phasing
        # line combine them (see the cut sheet).
        z_in = complex(src_a.z_real, src_a.z_imag)
    ar_boresight, ar_peak, sense = _polarization_summary(result)
    return DesignResult(
        spec=spec,
        base_factor=base_factor,
        delta=delta,
        z_in=z_in,
        phase_diff_deg=_phase_difference(result),
        sense=sense,
        ar_boresight_db=ar_boresight,
        ar_peak_db=ar_peak,
        deck=deck,
    )
