"""Crossed full-wave loop geometry for an eggbeater antenna.

The antenna is two full-wave loops in perpendicular vertical planes sharing a
common vertical (Z) axis: loop A in the XZ plane, loop B in the YZ plane.  Each
loop is approximated as a regular polygon of straight NEC wires, with the feed
segment placed at the bottom of the loop (closest to the reflector).
"""

import bisect
import math
from dataclasses import dataclass
from functools import cache

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

# Loop outline shapes. A squircle is a square with radiused corners: four
# straight sides joined by quarter-circle arcs of a given corner radius.
SHAPE_CIRCLE = "circle"
SHAPE_SQUARE = "square"
SHAPE_SQUIRCLE = "squircle"
LOOP_SHAPES = (SHAPE_CIRCLE, SHAPE_SQUARE, SHAPE_SQUIRCLE)
# Dense samples used to measure and resample a non-circular unit outline.
CURVE_SAMPLES = 2048
# Points per quarter-circle corner arc when densifying a squircle outline.
CORNER_ARC_SAMPLES = 64


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


def _square_unit_point(theta: float) -> tuple[float, float]:
    """Point on the unit square outline (spanning [-1, 1]) in direction theta."""
    c, s = math.cos(theta), math.sin(theta)
    reach = max(abs(c), abs(s))
    return c / reach, s / reach


@cache
def _dense_unit_square() -> tuple[tuple[float, float], ...]:
    """Closed dense polyline of the unit square, starting at the bottom."""
    return tuple(
        _square_unit_point(-math.pi / 2.0 + 2.0 * math.pi * i / CURVE_SAMPLES)
        for i in range(CURVE_SAMPLES + 1)
    )


def _cumulative_arc(points: tuple[tuple[float, float], ...]) -> list[float]:
    cum = [0.0]
    for (u0, v0), (u1, v1) in zip(points, points[1:], strict=False):
        cum.append(cum[-1] + math.hypot(u1 - u0, v1 - v0))
    return cum


def _resample_closed(
    dense: tuple[tuple[float, float], ...], segments: int
) -> list[tuple[float, float]]:
    """`segments` vertices at equal arc length, the first side straddling the
    start point of the dense outline (the bottom, so the feed sits there)."""
    cum = _cumulative_arc(dense)
    total = cum[-1]
    points = []
    for k in range(segments):
        target = (k - 0.5) / segments * total % total
        i = bisect.bisect_left(cum, target)
        if i <= 0:
            points.append(dense[0])
            continue
        s0, s1 = cum[i - 1], cum[i]
        frac = 0.0 if s1 == s0 else (target - s0) / (s1 - s0)
        (u0, v0), (u1, v1) = dense[i - 1], dense[i]
        points.append((u0 + frac * (u1 - u0), v0 + frac * (v1 - v0)))
    return points


def rounded_square_side(perimeter_m: float, corner_radius_m: float) -> float:
    """Bounding side of a rounded-corner square of the given perimeter.

    Perimeter = 4 straight sides of (side - 2r) plus four quarter arcs (2*pi*r):
    P = 4*(S - 2r) + 2*pi*r, so S = (P + (8 - 2*pi)*r) / 4.
    """
    return (perimeter_m + (8.0 - 2.0 * math.pi) * corner_radius_m) / 4.0


def _rounded_square_outline(
    side_m: float, radius_m: float
) -> tuple[tuple[float, float], ...]:
    """Dense (across, up) outline of a rounded square centred at the origin,
    starting at the bottom-centre so the feed lands at the bottom."""
    half = side_m / 2.0
    c = half - radius_m  # corner-arc centre offset from the origin on each axis
    points = [(0.0, -half)]
    # Four corners, counter-clockwise from bottom-right; each is a quarter arc
    # preceded by the straight run leading into it.
    corners = (
        (c, -c, -math.pi / 2.0, (c, -half)),  # bottom-right
        (c, c, 0.0, (half, c)),  # top-right
        (-c, c, math.pi / 2.0, (-c, half)),  # top-left
        (-c, -c, math.pi, (-half, -c)),  # bottom-left
    )
    for cx, cy, start_angle, run_end in corners:
        points.append(run_end)  # straight run up to the arc start
        for i in range(1, CORNER_ARC_SAMPLES + 1):
            angle = start_angle + (math.pi / 2.0) * i / CORNER_ARC_SAMPLES
            points.append(
                (cx + radius_m * math.cos(angle), cy + radius_m * math.sin(angle))
            )
    points.append((0.0, -half))  # close along the bottom-left straight run
    return tuple(points)


def loop_extent_m(
    perimeter_m: float, shape: str, corner_radius_m: float = 0.0
) -> float:
    """Across-dimension (bounding width) of a loop of the given perimeter:
    diameter for a circle, side for a square or squircle."""
    if shape == SHAPE_SQUIRCLE:
        return rounded_square_side(perimeter_m, corner_radius_m)
    unit = 2.0 * math.pi if shape == SHAPE_CIRCLE else _square_unit_perimeter()
    return 2.0 * perimeter_m / unit


@cache
def _square_unit_perimeter() -> float:
    return _cumulative_arc(_dense_unit_square())[-1]


def _loop_outline_points(
    shape: str, perimeter_m: float, corner_radius_m: float, segments: int
) -> list[tuple[float, float]]:
    """Loop outline vertices (across, up) in metres, feed side at the bottom."""
    if shape == SHAPE_CIRCLE:
        radius = loop_radius_m(perimeter_m)
        step = 2.0 * math.pi / segments
        start = -math.pi / 2.0 - step / 2.0
        return [
            (radius * math.cos(start + k * step), radius * math.sin(start + k * step))
            for k in range(segments)
        ]
    if shape == SHAPE_SQUARE:
        scale = perimeter_m / _square_unit_perimeter()
        return [
            (u * scale, v * scale)
            for u, v in _resample_closed(_dense_unit_square(), segments)
        ]
    side = rounded_square_side(perimeter_m, corner_radius_m)
    return _resample_closed(_rounded_square_outline(side, corner_radius_m), segments)


def _make_loop(
    plane: str,
    perimeter_m: float,
    corner_radius_m: float,
    center_z_m: float,
    conductor_radius_m: float,
    tag_base: int,
    segments: int,
    shape: str,
) -> Loop:
    """Build one polygonal loop of the given outline in the 'xz' or 'yz' plane.

    Side 0 is centred on the bottom of the loop, giving a well-defined feed
    location near the reflector.
    """
    points = []
    for across, up_offset in _loop_outline_points(
        shape, perimeter_m, corner_radius_m, segments
    ):
        up = center_z_m + up_offset
        points.append((across, 0.0, up) if plane == "xz" else (0.0, across, up))
    points.append(points[0])
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
    shape: str = SHAPE_CIRCLE,
    corner_radius_m: float = 0.0,
) -> Eggbeater:
    """Build crossed loops A (XZ plane) and B (YZ plane).

    corner_radius_m is the radius of the rounded corners for the squircle shape;
    it is ignored for circle and square. It must be positive and smaller than the
    equivalent circle radius (perimeter / 2*pi), past which no straight side
    remains and the shape would be a circle.
    """
    if shape not in LOOP_SHAPES:
        raise ValueError(f"unknown loop shape: {shape!r}")
    if shape == SHAPE_SQUIRCLE:
        max_radius = min(perimeter_a_m, perimeter_b_m) / (2.0 * math.pi)
        if not 0.0 < corner_radius_m < max_radius:
            raise ValueError(
                f"squircle corner radius {corner_radius_m:.4g} m must be in "
                f"(0, {max_radius:.4g}) for this loop perimeter"
            )
    loop_a = _make_loop(
        "xz",
        perimeter_a_m,
        corner_radius_m,
        center_z_m,
        conductor_radius_m,
        LOOP_A_TAG_BASE,
        segments,
        shape,
    )
    loop_b = _make_loop(
        "yz",
        perimeter_b_m,
        corner_radius_m,
        center_z_m,
        conductor_radius_m,
        LOOP_B_TAG_BASE,
        segments,
        shape,
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
