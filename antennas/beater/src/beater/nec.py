"""Emit NEC-2 decks, run nec2c, and parse its output."""

import math
import os
import subprocess
import tempfile
from dataclasses import dataclass

from .geometry import Wire

DEFAULT_NEC2C = "nec2c"
# RP card option code that reproduces the normal-mode power-gain pattern with
# the polarization/axial-ratio columns nec2c prints by default.
RP_OPTION_CODE = 1000


@dataclass(frozen=True)
class Source:
    """A voltage source (EX card) on one segment.

    Fields:
        tag: tag of the wire carrying the source segment.
        segment: 1-based segment number.
        v_real, v_imag: complex applied voltage.
    """

    tag: int
    segment: int
    v_real: float
    v_imag: float


@dataclass(frozen=True)
class RadiationGrid:
    """RP-card sampling grid over the upper hemisphere.

    Angles are in degrees; theta is measured from zenith.
    """

    ntheta: int
    nphi: int
    theta0: float
    phi0: float
    dtheta: float
    dphi: float


@dataclass(frozen=True)
class SourceResult:
    """Per-source result parsed from ANTENNA INPUT PARAMETERS."""

    tag: int
    segment: int
    z_real: float
    z_imag: float
    i_real: float
    i_imag: float

    @property
    def current_phase_deg(self) -> float:
        return math.degrees(math.atan2(self.i_imag, self.i_real))


@dataclass(frozen=True)
class PatternPoint:
    """One direction parsed from RADIATION PATTERNS."""

    theta_deg: float
    phi_deg: float
    total_gain_db: float
    # NEC axial ratio: minor/major axis, 0 (linear) .. 1 (circular).
    axial_ratio: float
    sense: str


@dataclass(frozen=True)
class NecResult:
    sources: tuple[SourceResult, ...]
    pattern: tuple[PatternPoint, ...]


def build_deck(
    comment_lines: list[str],
    wires: tuple[Wire, ...],
    sources: tuple[Source, ...],
    ground: bool,
    freq_mhz: float,
    grid: RadiationGrid,
) -> str:
    """Render a complete NEC-2 deck as text."""
    lines = [f"CM {c}" for c in comment_lines]
    lines.append("CE")
    for w in wires:
        lines.append(
            f"GW {w.tag} {w.segments} "
            f"{w.x1:.6f} {w.y1:.6f} {w.z1:.6f} "
            f"{w.x2:.6f} {w.y2:.6f} {w.z2:.6f} {w.radius_m:.6f}"
        )
    # GE flag -1: ground present but no wires connect to it (loops float above
    # the reflector); 0: free space.
    lines.append(f"GE {-1 if ground else 0}")
    if ground:
        # Perfect conducting ground plane approximates a solid metal reflector.
        lines.append("GN 1")
    lines.append("EK")
    for s in sources:
        lines.append(f"EX 0 {s.tag} {s.segment} 0 {s.v_real:.6f} {s.v_imag:.6f}")
    lines.append(f"FR 0 1 0 0 {freq_mhz:.6f} 0")
    lines.append(
        f"RP 0 {grid.ntheta} {grid.nphi} {RP_OPTION_CODE} "
        f"{grid.theta0:.3f} {grid.phi0:.3f} {grid.dtheta:.3f} {grid.dphi:.3f}"
    )
    lines.append("EN")
    return "\n".join(lines) + "\n"


def _is_float(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _parse_sources(lines: list[str], start: int) -> tuple[SourceResult, ...]:
    """Parse the ANTENNA INPUT PARAMETERS data rows.

    Columns: tag seg V_re V_im I_re I_im Z_re Z_im Y_re Y_im power.
    """
    results = []
    # Skip the two-line column header following the section title.
    i = start + 3
    while i < len(lines):
        tokens = lines[i].split()
        if len(tokens) < 11 or not _is_float(tokens[0]):
            break
        results.append(
            SourceResult(
                tag=int(tokens[0]),
                segment=int(tokens[1]),
                i_real=float(tokens[4]),
                i_imag=float(tokens[5]),
                z_real=float(tokens[6]),
                z_imag=float(tokens[7]),
            )
        )
        i += 1
    return tuple(results)


def _parse_pattern(lines: list[str], start: int) -> tuple[PatternPoint, ...]:
    """Parse RADIATION PATTERNS data rows.

    Layout: theta phi vert horiz total axial tilt [sense] e_theta_mag
    e_theta_phase e_phi_mag e_phi_phase.  The textual sense column is absent at
    directions where polarization is undefined (e.g. exact zenith).
    """
    points = []
    i = start
    seen_data = False
    while i < len(lines):
        tokens = lines[i].split()
        if len(tokens) >= 8 and _is_float(tokens[0]) and _is_float(tokens[1]):
            sense = "LINEAR" if _is_float(tokens[7]) else tokens[7]
            points.append(
                PatternPoint(
                    theta_deg=float(tokens[0]),
                    phi_deg=float(tokens[1]),
                    total_gain_db=float(tokens[4]),
                    axial_ratio=float(tokens[5]),
                    sense=sense,
                )
            )
            seen_data = True
        elif seen_data:
            break
        i += 1
    return tuple(points)


def parse_output(text: str) -> NecResult:
    """Parse nec2c output text into an NecResult."""
    lines = text.splitlines()
    sources: tuple[SourceResult, ...] = ()
    pattern: tuple[PatternPoint, ...] = ()
    for idx, line in enumerate(lines):
        if "ANTENNA INPUT PARAMETERS" in line:
            sources = _parse_sources(lines, idx)
        elif "RADIATION PATTERNS" in line:
            # Data rows begin after the three-line column header.
            pattern = _parse_pattern(lines, idx + 4)
    return NecResult(sources=sources, pattern=pattern)


def run_nec(deck: str, nec2c: str = DEFAULT_NEC2C) -> NecResult:
    """Run nec2c on a deck and return the parsed result."""
    with tempfile.TemporaryDirectory() as work:
        in_path = os.path.join(work, "in.nec")
        out_path = os.path.join(work, "out.txt")
        with open(in_path, "w") as handle:
            handle.write(deck)
        subprocess.run(
            [nec2c, "-i", in_path, "-o", out_path],
            check=True,
            capture_output=True,
            text=True,
        )
        with open(out_path) as handle:
            return parse_output(handle.read())
