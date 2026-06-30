import math

import pytest

from beater.geometry import (
    LOOP_A_TAG_BASE,
    LOOP_B_TAG_BASE,
    RADIAL_TAG_BASE,
    SHAPE_SQUARE,
    SHAPE_SQUIRCLE,
    loop_extent_m,
    loop_radius_m,
    make_eggbeater,
    make_radials,
    rounded_square_side,
    wavelength_m,
)


def _loop_perimeter(loop) -> float:
    return sum(math.dist((w.x1, w.y1, w.z1), (w.x2, w.y2, w.z2)) for w in loop.wires)


def test_wavelength():
    assert math.isclose(wavelength_m(299.792458), 1.0)


def test_loop_radius():
    assert math.isclose(loop_radius_m(2.0 * math.pi), 1.0)


def test_eggbeater_wire_count_and_tags():
    segments = 12
    egg = make_eggbeater(1.0, 1.0, 0.5, 0.001, segments)
    assert len(egg.loop_a.wires) == segments
    assert len(egg.loop_b.wires) == segments
    assert egg.loop_a.feed_tag == LOOP_A_TAG_BASE
    assert egg.loop_b.feed_tag == LOOP_B_TAG_BASE
    tags = {w.tag for w in egg.wires}
    assert len(tags) == 2 * segments


def test_feed_segment_is_lowest_point():
    egg = make_eggbeater(1.0, 1.0, 0.5, 0.001, 36)
    feed = egg.loop_a.wires[0]
    midpoint_z = (feed.z1 + feed.z2) / 2.0
    lowest = min(min(w.z1, w.z2) for w in egg.loop_a.wires)
    assert math.isclose(midpoint_z, lowest, abs_tol=1e-9)


def test_loops_lie_in_perpendicular_planes():
    egg = make_eggbeater(1.0, 1.0, 0.5, 0.001, 12)
    assert all(w.y1 == 0.0 and w.y2 == 0.0 for w in egg.loop_a.wires)
    assert all(w.x1 == 0.0 and w.x2 == 0.0 for w in egg.loop_b.wires)


def test_radials_share_hub_and_count():
    radials = make_radials(8, 0.5, 0.0, 0.0, 0.001, 4)
    assert len(radials) == 8
    assert {w.tag for w in radials} == set(range(RADIAL_TAG_BASE, RADIAL_TAG_BASE + 8))
    assert all(w.x1 == 0.0 and w.y1 == 0.0 and w.z1 == 0.0 for w in radials)


def test_radials_horizontal_when_no_droop():
    radials = make_radials(4, 0.5, 0.0, 0.0, 0.001, 2)
    assert all(math.isclose(w.z2, 0.0, abs_tol=1e-12) for w in radials)
    # Each radial spans its full length in the horizontal plane.
    assert all(math.isclose(math.hypot(w.x2, w.y2), 0.5) for w in radials)


def test_radials_droop_drops_tips():
    radials = make_radials(4, 1.0, 0.0, 30.0, 0.001, 2)
    assert all(math.isclose(w.z2, -0.5, abs_tol=1e-9) for w in radials)


def test_square_loop_perimeter_count_and_closure():
    segments, perimeter = 36, 4.0
    egg = make_eggbeater(perimeter, perimeter, 1.0, 0.001, segments, SHAPE_SQUARE)
    loop = egg.loop_a
    assert len(loop.wires) == segments
    # 36 divides by 4, so corners land on vertices and the perimeter is exact.
    assert math.isclose(_loop_perimeter(loop), perimeter, rel_tol=1e-6)
    first, last = loop.wires[0], loop.wires[-1]
    assert math.isclose(last.x2, first.x1) and math.isclose(last.z2, first.z1)


def test_square_loop_in_plane_and_feed_at_bottom():
    egg = make_eggbeater(4.0, 4.0, 1.0, 0.001, 36, SHAPE_SQUARE)
    loop = egg.loop_a
    assert all(w.y1 == 0.0 and w.y2 == 0.0 for w in loop.wires)
    feed_mid_z = (loop.wires[0].z1 + loop.wires[0].z2) / 2.0
    lowest = min(min(w.z1, w.z2) for w in loop.wires)
    assert math.isclose(feed_mid_z, lowest, abs_tol=1e-9)


def test_squircle_is_rounded_square():
    segments, perimeter, radius = 72, 4.0, 0.2
    egg = make_eggbeater(
        perimeter, perimeter, 1.0, 0.001, segments, SHAPE_SQUIRCLE, radius
    )
    loop = egg.loop_a
    assert len(loop.wires) == segments
    half = rounded_square_side(perimeter, radius) / 2.0
    # Loop lies in the XZ plane; measure across (x) and up (z) about the center.
    pts = [(w.x1, w.z1 - 1.0) for w in loop.wires]
    max_across = max(abs(a) for a, _ in pts)
    max_reach = max(math.hypot(a, b) for a, b in pts)
    # Straight sides reach the bounding box; corners are cut short of a square's
    # but still bulge past the inscribed circle -- i.e. a rounded square.
    assert math.isclose(max_across, half, rel_tol=1e-9)
    assert half < max_reach < half * math.sqrt(2.0)
    # Chords slightly under-run the arcs, so the wire perimeter sits just below.
    assert 0.99 * perimeter < _loop_perimeter(loop) <= perimeter


def test_squircle_has_straight_bottom_feed_side():
    egg = make_eggbeater(4.0, 4.0, 1.0, 0.001, 72, SHAPE_SQUIRCLE, 0.2)
    feed = egg.loop_a.wires[0]
    # The feed side is a straight run along the flat bottom (constant height).
    assert math.isclose(feed.z1, feed.z2, abs_tol=1e-9)
    lowest = min(min(w.z1, w.z2) for w in egg.loop_a.wires)
    assert math.isclose(feed.z1, lowest, abs_tol=1e-9)


def test_squircle_corner_radius_must_be_below_circle_radius():
    # At P / (2*pi) no straight side remains, so it is rejected.
    with pytest.raises(ValueError):
        make_eggbeater(4.0, 4.0, 1.0, 0.001, 36, SHAPE_SQUIRCLE, 4.0 / (2.0 * math.pi))
    with pytest.raises(ValueError):
        make_eggbeater(4.0, 4.0, 1.0, 0.001, 36, SHAPE_SQUIRCLE, 0.0)


def test_loop_extent_per_shape():
    # Circle: diameter = perimeter / pi. Square: side = perimeter / 4.
    assert math.isclose(loop_extent_m(2.0 * math.pi, "circle"), 2.0)
    assert math.isclose(loop_extent_m(4.0, SHAPE_SQUARE), 1.0)
    # Rounded-corner square: side follows the perimeter relation, and cutting the
    # corners makes the bounding side larger than a plain square of equal perimeter.
    assert math.isclose(
        loop_extent_m(4.0, SHAPE_SQUIRCLE, 0.2), rounded_square_side(4.0, 0.2)
    )
    assert loop_extent_m(4.0, SHAPE_SQUIRCLE, 0.2) > loop_extent_m(4.0, SHAPE_SQUARE)
