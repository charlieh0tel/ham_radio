"""Structured, JSON-serializable view of a tuned design.

result_to_dict is the single source of the derived numbers: the build cut list
(loop dimensions and the matching hardware) and the predicted performance. The
text cut sheet renders from this dict and --emit-result writes it verbatim, so
the numbers cannot diverge between outputs.

The result dict has three top-level sections (a fourth, "bandwidth", is added
only when a frequency sweep is requested):

    spec        the input spec (see spec.spec_to_dict).
    build       buildable cut list:
                  freq_mhz, wavelength_mm, phasing, loop_shape, reflector;
                  corner_radius_mm present for the squircle shape;
                  loop_center_height_wl/_mm and radials present with a reflector;
                  self phasing: detune_percent, large_loop, small_loop;
                  line phasing: loop, phasing_line_mm;
                  each loop dict is {perimeter_mm, width_mm} (width is the
                  across dimension: diameter, side, or squircle width);
                  match: series_element (null or {kind, value_nh|value_pf}),
                         transformer_z0_ohm, transformer_standard_coax_ohm,
                         transformer_length_mm.
    performance feedpoint and pattern figures of merit:
                  feed_z_ohm {real, imag}, feed_z_kind (feedpoint|per_loop),
                  vswr_unmatched, vswr_matched, loop_current_phase_deg,
                  sense, sense_requested, sense_achieved,
                  axial_ratio_cone_db, axial_ratio_peak_db, coverage_gain_dbi.
    bandwidth   vswr_2to1_mhz and axial_ratio_3db_mhz, each [low, high] or null.
"""

import json

from .design import (
    AR_TARGET_DB,
    MATCH_REACTANCE_WARN_OHMS,
    NEC_SENSE_TO_HAND,
    PHASING_SELF,
    REFLECTOR_NONE,
    REFLECTOR_RADIALS,
    VSWR_LIMIT,
    DesignResult,
    bandwidth_within,
    frequency_sweep,
    nearest_standard_coax,
    post_match_vswr,
    quarter_wave_match_z0,
    series_match_element,
    vswr,
)
from .geometry import SHAPE_SQUIRCLE, loop_extent_m, wavelength_m
from .spec import spec_to_dict

MM_PER_M = 1000.0
PF_PER_FARAD = 1.0e12
NH_PER_HENRY = 1.0e9
# Fraction of a wavelength in a quarter-wave line (phasing or transformer).
QUARTER_WAVE = 0.25


def _loop_dims(perimeter_m: float, shape: str, corner_radius_m: float) -> dict:
    return {
        "perimeter_mm": perimeter_m * MM_PER_M,
        "width_mm": loop_extent_m(perimeter_m, shape, corner_radius_m) * MM_PER_M,
    }


def _match_dict(result: DesignResult, wavelength: float) -> dict:
    spec = result.spec
    z = result.z_in
    z0 = quarter_wave_match_z0(z)
    series = None
    if abs(z.imag) > MATCH_REACTANCE_WARN_OHMS:
        kind, value = series_match_element(z, spec.freq_mhz)
        series = {"kind": kind}
        if kind == "capacitor":
            series["value_pf"] = value * PF_PER_FARAD
        else:
            series["value_nh"] = value * NH_PER_HENRY
    return {
        "series_element": series,
        "transformer_z0_ohm": z0,
        "transformer_standard_coax_ohm": nearest_standard_coax(z0),
        "transformer_length_mm": QUARTER_WAVE * wavelength * spec.match_vf * MM_PER_M,
    }


def _build_dict(result: DesignResult) -> dict:
    spec = result.spec
    wavelength = wavelength_m(spec.freq_mhz)
    build = {
        "freq_mhz": spec.freq_mhz,
        "wavelength_mm": wavelength * MM_PER_M,
        "phasing": spec.phasing,
        "loop_shape": spec.loop_shape,
        "reflector": spec.reflector,
    }
    if spec.reflector != REFLECTOR_NONE:
        build["loop_center_height_wl"] = spec.reflector_spacing_wl
        height_mm = spec.reflector_spacing_wl * wavelength * MM_PER_M
        build["loop_center_height_mm"] = height_mm
    if spec.reflector == REFLECTOR_RADIALS:
        build["radials"] = {
            "count": spec.radial_count,
            "length_mm": spec.radial_length_wl * wavelength * MM_PER_M,
            "droop_deg": spec.radial_droop_deg,
        }
    shape = spec.loop_shape
    corner_radius_m = (
        spec.corner_radius_wl * wavelength if shape == SHAPE_SQUIRCLE else 0.0
    )
    if shape == SHAPE_SQUIRCLE:
        build["corner_radius_mm"] = corner_radius_m * MM_PER_M
    if spec.phasing == PHASING_SELF:
        base = result.base_factor * wavelength
        build["detune_percent"] = result.delta * 100.0
        build["large_loop"] = _loop_dims(
            base * (1.0 + result.delta), shape, corner_radius_m
        )
        build["small_loop"] = _loop_dims(
            base * (1.0 - result.delta), shape, corner_radius_m
        )
    else:
        build["loop"] = _loop_dims(
            result.base_factor * wavelength, shape, corner_radius_m
        )
        build["phasing_line_mm"] = QUARTER_WAVE * wavelength * spec.coax_vf * MM_PER_M
    build["match"] = _match_dict(result, wavelength)
    return build


def _performance_dict(result: DesignResult) -> dict:
    spec = result.spec
    z = result.z_in
    achieved = NEC_SENSE_TO_HAND.get(result.sense)
    return {
        "feed_z_ohm": {"real": z.real, "imag": z.imag},
        "feed_z_kind": "feedpoint" if spec.phasing == PHASING_SELF else "per_loop",
        "vswr_unmatched": vswr(z),
        "vswr_matched": post_match_vswr(z),
        "loop_current_phase_deg": result.phase_diff_deg,
        "sense": (achieved.upper() if achieved else result.sense),
        "sense_requested": spec.sense.upper(),
        "sense_achieved": achieved == spec.sense,
        "axial_ratio_cone_db": result.ar_boresight_db,
        "axial_ratio_peak_db": result.ar_peak_db,
        "coverage_gain_dbi": result.coverage_gain_db,
    }


def _bandwidth_dict(result: DesignResult) -> dict:
    sweep = frequency_sweep(result)
    vswr_band = bandwidth_within([(p.freq_mhz, p.vswr) for p in sweep], VSWR_LIMIT)
    ar_band = bandwidth_within([(p.freq_mhz, p.ar_db) for p in sweep], AR_TARGET_DB)
    return {
        "vswr_2to1_mhz": list(vswr_band) if vswr_band else None,
        "axial_ratio_3db_mhz": list(ar_band) if ar_band else None,
    }


def result_to_dict(result: DesignResult, bandwidth: bool = False) -> dict:
    """Serialize a tuned design's cut list and performance to a plain dict.

    The frequency sweep (extra nec2c runs) is done only when bandwidth is set.
    """
    data = {
        "spec": spec_to_dict(result.spec),
        "build": _build_dict(result),
        "performance": _performance_dict(result),
    }
    if bandwidth:
        data["bandwidth"] = _bandwidth_dict(result)
    return data


def results_to_json(results: list[DesignResult], bandwidth: bool = False) -> str:
    """Serialize results to JSON; a single result becomes an object, not a list."""
    payload = [result_to_dict(r, bandwidth) for r in results]
    return json.dumps(payload[0] if len(payload) == 1 else payload, indent=2)
