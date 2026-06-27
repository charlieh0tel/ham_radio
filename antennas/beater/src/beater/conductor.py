"""Conductor cross-section models and conversion to a NEC equivalent radius.

NEC-2 models every wire as a round conductor specified by its radius.  Real
hardware is built from round wire or rectangular bar stock, so each cross-section
is reduced to the radius of a cylinder presenting the same external inductance
per unit length (matched via the self geometric-mean distance, GMD).
"""

import math
from dataclasses import dataclass

# A round wire of radius r has self-GMD = CIRCLE_GMD_FACTOR * r.
CIRCLE_GMD_FACTOR = math.exp(-0.25)
# Self-GMD of a rectangular cross-section, approximated as
# RECT_GMD_FACTOR * (width + thickness) for comparable width and thickness.
RECT_GMD_FACTOR = 0.2235
# Equivalent radius of a thin flat strip is STRIP_EQUIV_RADIUS_FACTOR * width
# (exact result from conformal mapping of a zero-thickness strip).
STRIP_EQUIV_RADIUS_FACTOR = 0.25
MM_PER_M = 1000.0


@dataclass(frozen=True)
class Conductor:
    """A conductor reduced to its NEC equivalent radius.

    Fields:
        description: human-readable stock description for decks and cut sheets.
        equivalent_radius_mm: radius of the equivalent round wire, millimetres.
    """

    description: str
    equivalent_radius_mm: float

    @property
    def equivalent_radius_m(self) -> float:
        return self.equivalent_radius_mm / MM_PER_M


def round_conductor(diameter_mm: float) -> Conductor:
    """Round wire or tube of the given outside diameter."""
    return Conductor(
        description=f"round, {diameter_mm:g} mm dia",
        equivalent_radius_mm=diameter_mm / 2.0,
    )


def strip_conductor(width_mm: float) -> Conductor:
    """Thin flat strip (thickness negligible) of the given width."""
    return Conductor(
        description=f"flat strip, {width_mm:g} mm wide",
        equivalent_radius_mm=STRIP_EQUIV_RADIUS_FACTOR * width_mm,
    )


def bar_conductor(width_mm: float, thickness_mm: float) -> Conductor:
    """Rectangular bar stock of the given width and thickness.

    A non-positive thickness degenerates to a flat strip.
    """
    if thickness_mm <= 0.0:
        return strip_conductor(width_mm)
    gmd = RECT_GMD_FACTOR * (width_mm + thickness_mm)
    return Conductor(
        description=f"bar, {width_mm:g} x {thickness_mm:g} mm",
        equivalent_radius_mm=gmd / CIRCLE_GMD_FACTOR,
    )
