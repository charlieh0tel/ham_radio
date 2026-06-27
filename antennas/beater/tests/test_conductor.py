import math

from beater.conductor import (
    CIRCLE_GMD_FACTOR,
    RECT_GMD_FACTOR,
    STRIP_EQUIV_RADIUS_FACTOR,
    bar_conductor,
    round_conductor,
    strip_conductor,
)


def test_round_radius_is_half_diameter():
    c = round_conductor(3.0)
    assert c.equivalent_radius_mm == 1.5
    assert c.equivalent_radius_m == 0.0015


def test_strip_radius_is_quarter_width():
    c = strip_conductor(12.0)
    assert c.equivalent_radius_mm == STRIP_EQUIV_RADIUS_FACTOR * 12.0


def test_bar_zero_thickness_degenerates_to_strip():
    assert (
        bar_conductor(10.0, 0.0).equivalent_radius_mm
        == strip_conductor(10.0).equivalent_radius_mm
    )


def test_bar_uses_gmd_formula():
    c = bar_conductor(12.0, 3.0)
    expected = RECT_GMD_FACTOR * (12.0 + 3.0) / CIRCLE_GMD_FACTOR
    assert math.isclose(c.equivalent_radius_mm, expected)
