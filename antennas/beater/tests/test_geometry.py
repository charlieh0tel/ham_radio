import math

from beater.geometry import (
    LOOP_A_TAG_BASE,
    LOOP_B_TAG_BASE,
    RADIAL_TAG_BASE,
    loop_radius_m,
    make_eggbeater,
    make_radials,
    wavelength_m,
)


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
