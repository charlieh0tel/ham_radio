import json

from beater.conductor import round_conductor
from beater.design import DesignResult, DesignSpec
from beater.result import result_to_dict, results_to_json


def _result(**spec_overrides) -> DesignResult:
    fields = dict(
        freq_mhz=145.9,
        conductor=round_conductor(5.0),
        reflector="radials",
        radial_droop_deg=40.0,
    )
    fields.update(spec_overrides)
    spec = DesignSpec(**fields)
    return DesignResult(
        spec=spec,
        base_factor=1.05,
        delta=0.07,
        z_in=complex(112.5, -16.0),
        phase_diff_deg=88.0,
        sense="RIGHT",
        ar_boresight_db=1.3,
        ar_peak_db=0.7,
        coverage_gain_db=0.34,
        deck="",
    )


def test_build_and_performance_sections():
    data = result_to_dict(_result())
    assert set(data) == {"spec", "build", "performance"}
    build = data["build"]
    assert build["large_loop"]["perimeter_mm"] > build["small_loop"]["perimeter_mm"]
    assert build["radials"]["count"] == 8
    # Capacitive feed (-16j) is canceled by a series inductor.
    assert build["match"]["series_element"]["kind"] == "inductor"
    assert build["match"]["transformer_standard_coax_ohm"] == 75.0
    perf = data["performance"]
    assert perf["feed_z_kind"] == "feedpoint"
    assert perf["coverage_gain_dbi"] == 0.34
    assert perf["sense"] == "RHCP"
    assert perf["sense_achieved"] is True


def test_line_phasing_build_has_phasing_line():
    build = result_to_dict(_result(phasing="line"))["build"]
    assert "loop" in build and "large_loop" not in build
    assert build["phasing_line_mm"] > 0.0


def test_line_phasing_feed_z_is_per_loop():
    perf = result_to_dict(_result(phasing="line"))["performance"]
    assert perf["feed_z_kind"] == "per_loop"


def test_bandwidth_absent_unless_requested():
    assert "bandwidth" not in result_to_dict(_result())


def test_results_to_json_single_is_object():
    assert isinstance(json.loads(results_to_json([_result()])), dict)


def test_results_to_json_list():
    payload = json.loads(results_to_json([_result(), _result(freq_mhz=436.0)]))
    assert isinstance(payload, list)
    assert len(payload) == 2
