"""Crossed full-wave loop geometry for an eggbeater antenna.

The antenna is two full-wave loops in perpendicular vertical planes sharing a
common vertical (Z) axis: loop A in the XZ plane, loop B in the YZ plane.  Each
loop is approximated as a regular polygon of straight NEC wires, with the feed
segment placed at the bottom of the loop (closest to the reflector).
"""

import math
from dataclasses import dataclass

# Speed of light expressed so that wavelength_m = LIGHT_MHZ_M / freq_mhz.
LIGHT_MHZ_M = 299.792458
# NEC tag numbers: loop A occupies [LOOP_A_TAG_BASE, +segments), loop B likewise.
# The bases are spaced wide enough that the per-side tags never overlap.
LOOP_A_TAG_BASE = 100
LOOP_B_TAG_BASE = 200
# Reflector radials occupy [RADIAL_TAG_BASE, +count).
RADIAL_TAG_BASE = 300
# Default polygon resolution; each side becomes one NEC segment.
DEFAULT_SEGMENTS = 36


def wavelength_m(freq_mhz: float) -> float:
    return LIGHT_MHZ_M / freq_mhz


@dataclass(frozen=True)
class Wire:
    """One straight NEC wire (GW card).

    Fields:
        tag: NEC tag number.
        segments: number of NEC segments along the wire.
        x1, y1, z1: first endpoint, metres.
        x2, y2, z2: second endpoint, metres.
        radius_m: conductor radius, metres.
    """

    tag: int
    segments: int
    x1: float
    y1: float
    z1: float
    x2: float
    y2: float
    z2: float
    radius_m: float


@dataclass(frozen=True)
class Loop:
    """A single full-wave loop.

    Fields:
        wires: ordered wires forming the closed polygon.
        feed_tag: tag of the wire carrying the feed segment.
        feed_segment: 1-based segment number within feed_tag.
    """

    wires: tuple[Wire, ...]
    feed_tag: int
    feed_segment: int


@dataclass(frozen=True)
class Eggbeater:
    """The pair of crossed loops."""

    loop_a: Loop
    loop_b: Loop

    @property
    def wires(self) -> tuple[Wire, ...]:
        return self.loop_a.wires + self.loop_b.wires


def loop_radius_m(perimeter_m: float) -> float:
    """Circle radius for a loop of the given perimeter."""
    return perimeter_m / (2.0 * math.pi)


def _make_loop(
    plane: str,
    perimeter_m: float,
    center_z_m: float,
    conductor_radius_m: float,
    tag_base: int,
    segments: int,
) -> Loop:
    """Build one polygonal loop in the 'xz' or 'yz' plane.

    Vertices are placed so that side 0 is centred on the bottom of the loop
    (angle -pi/2), giving a well-defined feed location near the reflector.
    """
    radius = loop_radius_m(perimeter_m)
    step = 2.0 * math.pi / segments
    start_angle = -math.pi / 2.0 - step / 2.0
    points = []
    for k in range(segments + 1):
        angle = start_angle + k * step
        across = radius * math.cos(angle)
        up = center_z_m + radius * math.sin(angle)
        if plane == "xz":
            points.append((across, 0.0, up))
        else:
            points.append((0.0, across, up))
    wires = tuple(
        Wire(
            tag=tag_base + k,
            segments=1,
            x1=points[k][0],
            y1=points[k][1],
            z1=points[k][2],
            x2=points[k + 1][0],
            y2=points[k + 1][1],
            z2=points[k + 1][2],
            radius_m=conductor_radius_m,
        )
        for k in range(segments)
    )
    return Loop(wires=wires, feed_tag=tag_base, feed_segment=1)


def make_eggbeater(
    perimeter_a_m: float,
    perimeter_b_m: float,
    center_z_m: float,
    conductor_radius_m: float,
    segments: int = DEFAULT_SEGMENTS,
) -> Eggbeater:
    """Build crossed loops A (XZ plane) and B (YZ plane)."""
    loop_a = _make_loop(
        "xz", perimeter_a_m, center_z_m, conductor_radius_m, LOOP_A_TAG_BASE, segments
    )
    loop_b = _make_loop(
        "yz", perimeter_b_m, center_z_m, conductor_radius_m, LOOP_B_TAG_BASE, segments
    )
    return Eggbeater(loop_a=loop_a, loop_b=loop_b)


def make_radials(
    count: int,
    length_m: float,
    hub_z_m: float,
    droop_deg: float,
    conductor_radius_m: float,
    segments_per_radial: int,
) -> tuple[Wire, ...]:
    """Build a reflector of evenly spaced radial wires from a common hub.

    Radials run from the hub on the Z axis outward in azimuth; a positive droop
    angle tilts them downward from horizontal. They share the hub coordinate, so
    NEC connects them there.
    """
    droop = math.radians(droop_deg)
    horizontal = length_m * math.cos(droop)
    drop = length_m * math.sin(droop)
    wires = []
    for i in range(count):
        azimuth = 2.0 * math.pi * i / count
        wires.append(
            Wire(
                tag=RADIAL_TAG_BASE + i,
                segments=segments_per_radial,
                x1=0.0,
                y1=0.0,
                z1=hub_z_m,
                x2=horizontal * math.cos(azimuth),
                y2=horizontal * math.sin(azimuth),
                z2=hub_z_m - drop,
                radius_m=conductor_radius_m,
            )
        )
    return tuple(wires)
