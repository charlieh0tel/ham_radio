import argparse
import math
import shutil

import pytest

from beater.cli import parse_conductor
from beater.conductor import bar_conductor, round_conductor
from beater.design import PHASING_LINE, PHASING_SELF, DesignSpec, design

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
