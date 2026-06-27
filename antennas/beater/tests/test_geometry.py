import math

from beater.geometry import (
    LOOP_A_TAG_BASE,
    LOOP_B_TAG_BASE,
    loop_radius_m,
    make_eggbeater,
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
