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
import time
from dataclasses import dataclass, replace

from .conductor import Conductor
from .geometry import (
    DEFAULT_SEGMENTS,
    SHAPE_CIRCLE,
    Wire,
    loop_radius_m,
    make_eggbeater,
    make_radials,
    wavelength_m,
)
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
REFLECTOR_RADIALS = "radials"
SENSE_RHCP = "rhcp"
SENSE_LHCP = "lhcp"

# Map nec2c's polarization sense column to a handedness constant.
NEC_SENSE_TO_HAND = {"RIGHT": SENSE_RHCP, "LEFT": SENSE_LHCP}

# Target NEC segment length along a radial, in wavelengths.
RADIAL_SEGMENT_WL = 0.05

# Feed phase of loop B for the quarter-wave-line scheme.
LINE_PHASE_DEG = -90.0
REFERENCE_IMPEDANCE_OHMS = 50.0
# Common coax characteristic impedances suggested for the matching section.
STANDARD_COAX_OHMS = (50.0, 75.0, 93.0)
# Residual feedpoint reactance above which a series tuning element is sized.
MATCH_REACTANCE_WARN_OHMS = 10.0
HZ_PER_MHZ = 1.0e6

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
# Coverage gain is the worst-case gain over the operational cone,
# theta <= COVERAGE_THETA_DEG from zenith (elevation >= 30 deg): the lowest gain
# a pass sees anywhere in the high-elevation sky the reflector is tuned for.
COVERAGE_THETA_DEG = 60.0
# Total gains at or below this level mark pattern nulls and are ignored.
NULL_GAIN_DB = -100.0

# Reflector optimization: continuous search bounds and the axial-ratio budget.
SPACING_BOUNDS_WL = (0.15, 0.40)
DROOP_BOUNDS_DEG = (0.0, 50.0)
# Coordinate-descent tolerances (the placement is refined to this resolution).
SPACING_TOLERANCE_WL = 0.005
DROOP_TOLERANCE_DEG = 1.0
# Alternating spacing/droop passes per radial count.
PLACEMENT_SWEEPS = 2
# Radial counts searched, ascending; the optimizer keeps the fewest that meets
# the objectives (fewer radials is cheaper, lighter, and less wind load).
RADIAL_COUNT_GRID = (3, 4, 6, 8)
AR_TARGET_DB = 3.0
# Cost penalty per dB of axial ratio above AR_TARGET_DB.
AR_PENALTY_PER_DB = 1.0
# A radial count is acceptable when the tuned design holds axial ratio within
# AR_TARGET_DB and post-match VSWR within this limit.
FEASIBLE_VSWR = 1.5

# Frequency-sweep defaults and the SWR threshold whose bandwidth is reported.
SWEEP_SPAN_FRACTION = 0.10
SWEEP_POINTS = 41
VSWR_LIMIT = 2.0


@dataclass(frozen=True)
class DesignSpec:
    """Inputs that define a design problem.

    Fields:
        freq_mhz: design frequency.
        conductor: conductor cross-section.
        phasing: PHASING_SELF or PHASING_LINE.
        reflector: REFLECTOR_NONE, REFLECTOR_GROUND, or REFLECTOR_RADIALS.
        reflector_spacing_wl: loop-centre height above the reflector, wavelengths.
        coax_vf: velocity factor of the phasing-line coax (line scheme).
        match_vf: velocity factor of the matching-section coax.
        sense: desired polarization, SENSE_RHCP or SENSE_LHCP.
        loop_shape: loop outline, SHAPE_CIRCLE, SHAPE_SQUARE, or SHAPE_SQUIRCLE.
        corner_radius_wl: rounded-corner radius for the squircle shape, in
            wavelengths (ignored for circle and square).
        segments: polygon sides per loop.
        radial_count: number of reflector radials (radials scheme).
        radial_length_wl: length of each radial, wavelengths.
        radial_droop_deg: downward tilt of the radials from horizontal.
        label: optional human-readable name for output (e.g. "2 m").
        notes: optional free-text design intent; carried through optimization.
        optimization: provenance set when the spec came from optimize_reflector
            (the input spec and the search parameters); None otherwise.
        nec2c: nec2c executable name or path.

    Only freq_mhz and conductor are required; every other field has a default
    that serves as the single source of defaults for both the CLI and JSON.
    """

    freq_mhz: float
    conductor: Conductor
    phasing: str = PHASING_SELF
    reflector: str = REFLECTOR_NONE
    reflector_spacing_wl: float = 0.25
    coax_vf: float = 0.66
    match_vf: float = 0.66
    sense: str = SENSE_RHCP
    loop_shape: str = SHAPE_CIRCLE
    corner_radius_wl: float = 0.05
    segments: int = DEFAULT_SEGMENTS
    radial_count: int = 8
    radial_length_wl: float = 0.27
    radial_droop_deg: float = 0.0
    label: str | None = None
    notes: str | None = None
    optimization: "Optimization | None" = None
    nec2c: str = DEFAULT_NEC2C


@dataclass(frozen=True)
class Optimization:
    """Provenance of a spec produced by optimize_reflector.

    Fields:
        input: the spec as received, before optimization.
        method: description of the spacing/droop search method.
        spacing_bounds_wl: (low, high) reflector spacing searched, wavelengths.
        droop_bounds_deg: (low, high) radial droop searched, degrees.
        spacing_tolerance_wl: spacing resolution the descent converged to.
        droop_tolerance_deg: droop resolution the descent converged to.
        sweeps: alternating spacing/droop passes per radial count.
        radial_count_grid: radial counts searched.
        ar_target_db: axial-ratio budget the search held to.
        ar_penalty_per_db: cost penalty per dB of axial ratio above the budget.
        feasible_vswr: post-match VSWR a radial count had to meet to be kept.
        objective: short description of what was minimized.
        elapsed_s: wall-clock seconds the search took.
    """

    input: DesignSpec
    method: str
    spacing_bounds_wl: tuple[float, float]
    droop_bounds_deg: tuple[float, float]
    spacing_tolerance_wl: float
    droop_tolerance_deg: float
    sweeps: int
    radial_count_grid: tuple[int, ...]
    ar_target_db: float
    ar_penalty_per_db: float
    feasible_vswr: float
    objective: str
    elapsed_s: float


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
        coverage_gain_db: worst-case total gain over the coverage cone
            (theta <= COVERAGE_THETA_DEG), dBi.
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
    coverage_gain_db: float
    deck: str


def _center_z_m(spec: DesignSpec, wavelength: float, perimeter_m: float) -> float:
    if spec.reflector in (REFLECTOR_GROUND, REFLECTOR_RADIALS):
        # Loop centre sits the given spacing above the reflector plane (z = 0).
        return spec.reflector_spacing_wl * wavelength
    # In free space the absolute height is irrelevant; keep the loop above the
    # origin for readable coordinates.
    return loop_radius_m(perimeter_m)


def _reflector_wires(spec: DesignSpec, wavelength: float):
    """Radial reflector wires below the loops, or none for other schemes."""
    if spec.reflector != REFLECTOR_RADIALS:
        return ()
    length_m = spec.radial_length_wl * wavelength
    segments_per_radial = max(1, round(spec.radial_length_wl / RADIAL_SEGMENT_WL))
    return make_radials(
        count=spec.radial_count,
        length_m=length_m,
        hub_z_m=0.0,
        droop_deg=spec.radial_droop_deg,
        conductor_radius_m=spec.conductor.equivalent_radius_m,
        segments_per_radial=segments_per_radial,
    )


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
    run_freq_mhz: float | None = None,
    grid: RadiationGrid | None = None,
) -> tuple[NecResult, str]:
    """Run nec2c once for the given perimeters and feed phase.

    Geometry is always scaled to the design frequency; run_freq_mhz overrides
    only the analysis frequency (the FR card), so the fixed physical antenna can
    be swept across a band.  grid overrides the radiation-pattern sampling (for
    a fine elevation cut).  Sources are ordered loop A then loop B, matching
    nec2c's reporting order.
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
        spec.loop_shape,
        spec.corner_radius_wl * wavelength,
    )
    sources = _sources(spec, egg, phase_b_deg)
    wires = egg.wires + _reflector_wires(spec, wavelength)
    deck = build_deck(
        _comment_lines(spec),
        wires,
        sources,
        ground=spec.reflector == REFLECTOR_GROUND,
        freq_mhz=run_freq_mhz if run_freq_mhz is not None else spec.freq_mhz,
        grid=grid if grid is not None else DEFAULT_GRID,
    )
    return run_nec(deck, spec.nec2c), deck


def tuned_geometry(
    result: DesignResult,
) -> tuple[tuple[Wire, ...], tuple[tuple[float, float, float], ...]]:
    """Reconstruct the tuned wire model and the two loop feed points.

    Built from the same geometry calls as analyze(), so a 3-D view matches the
    deck without parsing it. Returns the loop and reflector wires and the feed
    points (midpoint of each loop's bottom feed wire), in metres.
    """
    spec = result.spec
    wavelength = wavelength_m(spec.freq_mhz)
    factor_a, factor_b, _ = _operating_point(
        result.base_factor, result.delta, spec.phasing, flip=False
    )
    perimeter_a = factor_a * wavelength
    center_z = _center_z_m(spec, wavelength, perimeter_a)
    egg = make_eggbeater(
        perimeter_a,
        factor_b * wavelength,
        center_z,
        spec.conductor.equivalent_radius_m,
        spec.segments,
        spec.loop_shape,
        spec.corner_radius_wl * wavelength,
    )
    wires = egg.wires + _reflector_wires(spec, wavelength)
    feeds = tuple(
        ((w.x1 + w.x2) / 2.0, (w.y1 + w.y2) / 2.0, (w.z1 + w.z2) / 2.0)
        for w in (egg.loop_a.wires[0], egg.loop_b.wires[0])
    )
    return wires, feeds


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


def _golden_section_min(func, low: float, high: float, tolerance: float) -> float:
    """Golden-section minimizer of a unimodal scalar function on [low, high]."""
    x1 = high - GOLDEN_RATIO * (high - low)
    x2 = low + GOLDEN_RATIO * (high - low)
    f1, f2 = func(x1), func(x2)
    while high - low > tolerance:
        if f1 < f2:
            high, x2, f2 = x2, x1, f1
            x1 = high - GOLDEN_RATIO * (high - low)
            f1 = func(x1)
        else:
            low, x1, f1 = x1, x2, f2
            x2 = low + GOLDEN_RATIO * (high - low)
            f2 = func(x2)
    return (low + high) / 2.0


def _resonant_factor(spec: DesignSpec) -> float:
    """Find the perimeter factor giving zero loop reactance (delta = 0)."""

    def reactance(factor: float) -> float:
        result, _ = analyze(spec, factor, factor, 0.0)
        return result.sources[0].z_imag

    return _secant(reactance, 1.0, 1.05, FACTOR_BOUNDS, REACTANCE_TOLERANCE_OHMS)


def _phase_difference(result: NecResult) -> float:
    return result.sources[0].current_phase_deg - result.sources[1].current_phase_deg


def _combined_feed_z(result: NecResult) -> complex:
    """Parallel feedpoint impedance of the self-phased loops (common 1 V feed)."""
    i_total = complex(result.sources[0].i_real, result.sources[0].i_imag) + complex(
        result.sources[1].i_real, result.sources[1].i_imag
    )
    if i_total == 0:
        return cmath.inf
    return 1.0 / i_total


def _antenna_feed_z(result: NecResult, phasing: str) -> complex:
    """Antenna feedpoint impedance for the scheme (combined self, per-loop line)."""
    if phasing == PHASING_SELF:
        return _combined_feed_z(result)
    return complex(result.sources[0].z_real, result.sources[0].z_imag)


def series_match_element(z: complex, freq_mhz: float) -> tuple[str, float]:
    """Series element that cancels the feedpoint reactance.

    Returns the element kind ('inductor' or 'capacitor') and its value, in
    henries or farads.  Resizing the loops to null the reactance would move the
    axial-ratio optimum, so the reactance is instead tuned out at the feed.
    """
    omega = 2.0 * math.pi * freq_mhz * HZ_PER_MHZ
    if z.imag > 0.0:
        # Inductive feed: a series capacitor of equal reactance cancels it.
        return "capacitor", 1.0 / (omega * z.imag)
    # Capacitive feed: a series inductor cancels it.
    return "inductor", -z.imag / omega


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


def _coverage_gain_db(result: NecResult) -> float:
    """Worst-case total gain (dBi) over the coverage cone.

    The minimum over theta <= COVERAGE_THETA_DEG is the lowest gain a pass sees
    in the high-elevation sky, so it bounds worst-case link margin there.
    """
    cone = [
        p.total_gain_db
        for p in result.pattern
        if p.theta_deg <= COVERAGE_THETA_DEG and p.total_gain_db > NULL_GAIN_DB
    ]
    if not cone:
        return -math.inf
    return min(cone)


def _self_phase_delta(spec: DesignSpec, base_factor: float) -> float:
    """Detune fraction minimizing boresight axial ratio (golden-section search)."""

    def cost(delta: float) -> float:
        result, _ = analyze(
            spec, base_factor * (1.0 + delta), base_factor * (1.0 - delta), 0.0
        )
        return _boresight_ar_db(result)

    return _golden_section_min(cost, *DELTA_BOUNDS, DELTA_TOLERANCE)


def _boresight_sense(result: NecResult) -> str:
    """Polarization sense at the most circular point in the coverage cone."""
    cone = [
        p
        for p in result.pattern
        if p.theta_deg <= BORESIGHT_THETA_DEG and p.total_gain_db > NULL_GAIN_DB
    ]
    if not cone:
        return "UNKNOWN"
    best = min(cone, key=lambda p: _axial_ratio_db(p.axial_ratio))
    return best.sense


def _polarization_summary(result: NecResult) -> tuple[float, float, str]:
    """Boresight axial ratio (dB), peak axial ratio (dB), and boresight sense."""
    usable = [p for p in result.pattern if p.total_gain_db > NULL_GAIN_DB]
    if not usable:
        return math.inf, math.inf, "UNKNOWN"
    peak = max(usable, key=lambda p: p.total_gain_db)
    return (
        _boresight_ar_db(result),
        _axial_ratio_db(peak.axial_ratio),
        _boresight_sense(result),
    )


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


def post_match_vswr(z: complex, reference: float = REFERENCE_IMPEDANCE_OHMS) -> float:
    """SWR at the design frequency after the standard-coax match network.

    The series element cancels the reactance and a nearest-standard-coax
    quarter-wave transformer scales the resistance toward the reference.
    """
    z0 = nearest_standard_coax(quarter_wave_match_z0(z))
    transformed = z0 * z0 / z.real
    return vswr(complex(transformed, 0.0), reference)


def _operating_point(
    base_factor: float, delta: float, phasing: str, flip: bool
) -> tuple[float, float, float]:
    """Loop perimeters and feed phase for one polarization orientation.

    Flipping reverses the handedness: it swaps which loop is large (self) or the
    sign of the feed phase (line).
    """
    if phasing == PHASING_SELF:
        sign = -1.0 if flip else 1.0
        return (
            base_factor * (1.0 + sign * delta),
            base_factor * (1.0 - sign * delta),
            0.0,
        )
    return base_factor, base_factor, -LINE_PHASE_DEG if flip else LINE_PHASE_DEG


def design(spec: DesignSpec) -> DesignResult:
    """Tune an eggbeater to the spec and return the result.

    Resonance and detune are handedness-independent, so they are solved once;
    the orientation is then chosen (and verified against nec2c) to deliver the
    requested polarization sense.
    """
    base_factor = _resonant_factor(spec)
    delta = (
        _self_phase_delta(spec, base_factor) if spec.phasing == PHASING_SELF else 0.0
    )

    # Build with the default orientation, then flip once if nec2c reports the
    # opposite sense from the one requested.
    flip = False
    for _ in range(2):
        factor_a, factor_b, phase_b = _operating_point(
            base_factor, delta, spec.phasing, flip
        )
        result, deck = analyze(spec, factor_a, factor_b, phase_b)
        ar_boresight, ar_peak, sense = _polarization_summary(result)
        if NEC_SENSE_TO_HAND.get(sense, spec.sense) == spec.sense:
            break
        flip = True

    # For self phasing this is the combined parallel feed; for line phasing it is
    # one loop's driving impedance (the tee plus phasing line combine them).
    z_in = _antenna_feed_z(result, spec.phasing)
    return DesignResult(
        spec=spec,
        base_factor=base_factor,
        delta=delta,
        z_in=z_in,
        phase_diff_deg=_phase_difference(result),
        sense=sense,
        ar_boresight_db=ar_boresight,
        ar_peak_db=ar_peak,
        coverage_gain_db=_coverage_gain_db(result),
        deck=deck,
    )


def _reflector_cost(result: DesignResult) -> float:
    """Optimization cost: post-match SWR, penalized for excess axial ratio."""
    excess = max(0.0, result.ar_boresight_db - AR_TARGET_DB)
    return post_match_vswr(result.z_in) + AR_PENALTY_PER_DB * excess


def _reflector_feasible(result: DesignResult) -> bool:
    """Whether a tuned design meets the axial-ratio and match objectives."""
    return (
        result.ar_boresight_db <= AR_TARGET_DB
        and post_match_vswr(result.z_in) <= FEASIBLE_VSWR
    )


def _best_placement(
    spec: DesignSpec, count: int, optimize_droop: bool
) -> tuple[float, DesignSpec, DesignResult]:
    """Coordinate-descent (spacing, droop) placement for a fixed radial count.

    Golden-section minimizes the match cost along each axis in turn, alternating
    for PLACEMENT_SWEEPS passes. The cost surface is smooth and unimodal, so a
    few sweeps reach a finer optimum than a fixed grid and never snap to a grid
    edge. Droop is held at zero for a ground reflector (no radials to tilt).
    """

    def cost_of(spacing: float, droop: float) -> float:
        candidate = replace(
            spec,
            radial_count=count,
            reflector_spacing_wl=spacing,
            radial_droop_deg=droop,
            optimization=None,
        )
        return _reflector_cost(design(candidate))

    spacing = sum(SPACING_BOUNDS_WL) / 2.0
    droop = sum(DROOP_BOUNDS_DEG) / 2.0 if optimize_droop else 0.0
    for _ in range(PLACEMENT_SWEEPS):
        spacing = _golden_section_min(
            lambda s, d=droop: cost_of(s, d), *SPACING_BOUNDS_WL, SPACING_TOLERANCE_WL
        )
        if optimize_droop:
            droop = _golden_section_min(
                lambda d, s=spacing: cost_of(s, d),
                *DROOP_BOUNDS_DEG,
                DROOP_TOLERANCE_DEG,
            )

    candidate = replace(
        spec,
        radial_count=count,
        reflector_spacing_wl=spacing,
        radial_droop_deg=droop,
        optimization=None,
    )
    result = design(candidate)
    return _reflector_cost(result), candidate, result


def optimize_reflector(spec: DesignSpec) -> DesignSpec:
    """Search radial count, spacing, and droop; return the best spec.

    A spec -> spec transform: the returned spec differs from the input only in
    the reflector geometry that best serves the design. Radial count is searched
    ascending and the fewest that meets the objectives (axial ratio within
    AR_TARGET_DB, post-match VSWR within FEASIBLE_VSWR) is kept; for each count a
    coordinate descent finds the lowest-cost spacing/droop placement. If no count
    is feasible the lowest-cost candidate overall is returned. Droop and count
    apply only to radials; a ground reflector searches spacing alone.
    """
    radials = spec.reflector == REFLECTOR_RADIALS
    counts = tuple(sorted(RADIAL_COUNT_GRID if radials else (spec.radial_count,)))
    start = time.perf_counter()

    chosen: DesignSpec | None = None
    fallback: tuple[float, DesignSpec] | None = None
    for count in counts:
        cost, candidate, result = _best_placement(spec, count, optimize_droop=radials)
        if fallback is None or cost < fallback[0]:
            fallback = (cost, candidate)
        if _reflector_feasible(result):
            chosen = candidate
            break
    best_spec = chosen if chosen is not None else fallback[1]

    provenance = Optimization(
        input=replace(spec, optimization=None),
        method="coordinate descent (golden-section per axis)",
        spacing_bounds_wl=SPACING_BOUNDS_WL,
        droop_bounds_deg=DROOP_BOUNDS_DEG if radials else (0.0, 0.0),
        spacing_tolerance_wl=SPACING_TOLERANCE_WL,
        droop_tolerance_deg=DROOP_TOLERANCE_DEG if radials else 0.0,
        sweeps=PLACEMENT_SWEEPS,
        radial_count_grid=counts,
        ar_target_db=AR_TARGET_DB,
        ar_penalty_per_db=AR_PENALTY_PER_DB,
        feasible_vswr=FEASIBLE_VSWR,
        objective="fewest radials meeting AR and VSWR, then minimize match cost",
        elapsed_s=round(time.perf_counter() - start, 3),
    )
    return replace(best_spec, optimization=provenance)


def _matched_input_z(
    z_ant: complex,
    freq_mhz: float,
    design_freq_mhz: float,
    z_center: complex,
    match_vf: float,
) -> complex:
    """Input impedance after the match network sized at the design frequency.

    The series element (sized from z_center) and the quarter-wave transformer
    are fixed by the design; here they are evaluated at freq_mhz.
    """
    omega = 2.0 * math.pi * freq_mhz * HZ_PER_MHZ
    kind, value = series_match_element(z_center, design_freq_mhz)
    series_reactance = omega * value if kind == "inductor" else -1.0 / (omega * value)
    z_after_series = z_ant + 1j * series_reactance

    z0 = nearest_standard_coax(quarter_wave_match_z0(z_center))
    # The line is a quarter wave at the design frequency, so its electrical
    # length scales linearly with frequency.
    theta = (math.pi / 2.0) * (freq_mhz / design_freq_mhz)
    tan_theta = math.tan(theta)
    return (
        z0
        * (z_after_series + 1j * z0 * tan_theta)
        / (z0 + 1j * z_after_series * tan_theta)
    )


@dataclass(frozen=True)
class SweepPoint:
    """One frequency-sweep sample.

    Fields:
        freq_mhz: analysis frequency.
        vswr: SWR at 50 ohm after the fixed match network.
        ar_db: boresight axial ratio (dB; 0 is perfect circular).
    """

    freq_mhz: float
    vswr: float
    ar_db: float


def frequency_sweep(
    result: DesignResult,
    span_fraction: float = SWEEP_SPAN_FRACTION,
    points: int = SWEEP_POINTS,
) -> list[SweepPoint]:
    """Matched SWR and boresight axial ratio versus frequency.

    The tuned physical geometry is held fixed and swept across +/- span_fraction;
    the match network is fixed at the design frequency.
    """
    spec = result.spec
    design_freq = spec.freq_mhz
    factor_a, factor_b, phase_b = _operating_point(
        result.base_factor, result.delta, spec.phasing, flip=False
    )
    low = design_freq * (1.0 - span_fraction)
    high = design_freq * (1.0 + span_fraction)
    sweep = []
    for i in range(points):
        freq = low + (high - low) * i / (points - 1)
        nec, _ = analyze(spec, factor_a, factor_b, phase_b, run_freq_mhz=freq)
        z_ant = _antenna_feed_z(nec, spec.phasing)
        z_in = _matched_input_z(z_ant, freq, design_freq, result.z_in, spec.match_vf)
        sweep.append(SweepPoint(freq, vswr(z_in), _boresight_ar_db(nec)))
    return sweep


def bandwidth_within(
    pairs: list[tuple[float, float]], limit: float
) -> tuple[float, float] | None:
    """Contiguous frequency band around the centre where value <= limit.

    Each pair is (freq_mhz, value). Edges are linearly interpolated between
    samples. Returns (low, high) MHz, or None if the centre already exceeds the
    limit.
    """
    center = len(pairs) // 2
    if pairs[center][1] > limit:
        return None

    def edge(indices) -> float:
        previous = center
        for i in indices:
            freq, value = pairs[i]
            if value > limit:
                f0, v0 = pairs[previous]
                # Interpolate the crossing between previous and this sample.
                frac = (limit - v0) / (value - v0)
                return f0 + (freq - f0) * frac
            previous = i
        return pairs[indices[-1]][0]

    low_edge = edge(range(center - 1, -1, -1))
    high_edge = edge(range(center + 1, len(pairs)))
    return low_edge, high_edge
