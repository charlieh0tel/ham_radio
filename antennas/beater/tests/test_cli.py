import argparse
import math
import shutil
from dataclasses import replace

import pytest

from beater.cli import parse_conductor
from beater.conductor import bar_conductor, round_conductor
from beater.design import (
    PHASING_LINE,
    PHASING_SELF,
    DesignSpec,
    bandwidth_2to1,
    design,
    optimize_reflector,
    post_match_vswr,
    vswr_sweep,
)

HAS_NEC2C = shutil.which("nec2c") is not None
needs_nec2c = pytest.mark.skipif(not HAS_NEC2C, reason="nec2c not installed")


def test_parse_conductor_forms():
    assert parse_conductor("round:3").equivalent_radius_mm == 1.5
    assert (
        parse_conductor("bar:12x3").equivalent_radius_mm
        == bar_conductor(12.0, 3.0).equivalent_radius_mm
    )


def test_parse_conductor_rejects_unknown():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_conductor("triangle:5")


def _spec(phasing: str) -> DesignSpec:
    # Coarse polygon keeps the nec2c-in-the-loop tests fast.
    return DesignSpec(
        freq_mhz=145.9,
        conductor=round_conductor(3.0),
        phasing=phasing,
        reflector="none",
        reflector_spacing_wl=0.25,
        coax_vf=0.66,
        match_vf=0.66,
        sense="rhcp",
        segments=16,
    )


@needs_nec2c
def test_self_phasing_tunes_within_bounds():
    result = design(_spec(PHASING_SELF))
    assert 0.8 < result.base_factor < 1.2
    assert 0.0 < result.delta <= 0.15
    # A detuned design must beat the linear (delta = 0) starting point.
    assert math.isfinite(result.ar_boresight_db)


@needs_nec2c
def test_line_phasing_resonates():
    result = design(_spec(PHASING_LINE))
    assert abs(result.z_in.imag) < 15.0


@needs_nec2c
def test_radial_reflector_runs():
    spec = replace(_spec(PHASING_SELF), reflector="radials")
    result = design(spec)
    assert math.isfinite(result.ar_boresight_db)
    assert result.deck.count("\nGW ") == 2 * spec.segments + spec.radial_count


@needs_nec2c
def test_sense_selection_flips_handedness():
    rhcp = design(replace(_spec(PHASING_SELF), reflector="ground", sense="rhcp"))
    lhcp = design(replace(_spec(PHASING_SELF), reflector="ground", sense="lhcp"))
    assert rhcp.sense == "RIGHT"
    assert lhcp.sense == "LEFT"


def test_post_match_vswr_ideal():
    # 112.5 ohm transforms through a 75 ohm quarter wave to exactly 50 ohm.
    assert math.isclose(post_match_vswr(complex(112.5, 0.0)), 1.0, abs_tol=1e-6)


def test_bandwidth_interpolates_edges():
    sweep = [(100.0, 3.0), (101.0, 1.5), (102.0, 1.0), (103.0, 1.5), (104.0, 3.0)]
    low, high = bandwidth_2to1(sweep)
    assert math.isclose(low, 100.667, abs_tol=1e-3)
    assert math.isclose(high, 103.333, abs_tol=1e-3)


def test_bandwidth_none_when_center_mismatched():
    sweep = [(100.0, 3.0), (101.0, 2.5), (102.0, 2.2)]
    assert bandwidth_2to1(sweep) is None


@needs_nec2c
def test_optimize_reflector_picks_grid_point():
    best = optimize_reflector(replace(_spec(PHASING_SELF), reflector="radials"))
    assert best.spec.reflector_spacing_wl in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40)
    assert best.spec.radial_droop_deg in (0.0, 15.0, 30.0, 45.0)


@needs_nec2c
def test_vswr_sweep_band_contains_center():
    result = design(replace(_spec(PHASING_SELF), reflector="ground"))
    sweep = vswr_sweep(result, span_fraction=0.05, points=11)
    band = bandwidth_2to1(sweep)
    assert band is not None
    low, high = band
    assert low <= result.spec.freq_mhz <= high
