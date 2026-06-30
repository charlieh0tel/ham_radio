from beater.conductor import bar_conductor, round_conductor
from beater.design import DesignSpec, Optimization
from beater.spec import (
    spec_from_dict,
    spec_to_dict,
    specs_from_json,
    specs_to_json,
)


def _spec(**overrides) -> DesignSpec:
    base = dict(freq_mhz=145.9, conductor=round_conductor(5.0))
    base.update(overrides)
    return DesignSpec(**base)


def test_spec_round_trip_round_conductor():
    spec = _spec(reflector="radials", radial_droop_deg=45.0, sense="lhcp")
    assert spec_from_dict(spec_to_dict(spec)) == spec


def test_spec_round_trip_square_loop():
    spec = _spec(loop_shape="square")
    assert spec_to_dict(spec)["loop_shape"] == "square"
    assert spec_from_dict(spec_to_dict(spec)) == spec


def test_spec_round_trip_squircle_loop():
    spec = _spec(loop_shape="squircle", corner_radius_wl=0.04)
    data = spec_to_dict(spec)
    assert data["loop_shape"] == "squircle"
    assert data["corner_radius_wl"] == 0.04
    assert spec_from_dict(data) == spec


def test_spec_round_trip_bar_conductor():
    spec = _spec(conductor=bar_conductor(12.7, 3.2))
    assert spec_from_dict(spec_to_dict(spec)) == spec


def test_spec_round_trip_with_optimization():
    base = _spec()
    opt = Optimization(
        input=base,
        method="coordinate descent (golden-section per axis)",
        spacing_bounds_wl=(0.15, 0.40),
        droop_bounds_deg=(0.0, 50.0),
        spacing_tolerance_wl=0.005,
        droop_tolerance_deg=1.0,
        sweeps=2,
        radial_count_grid=(3, 4, 6, 8),
        ar_target_db=3.0,
        ar_penalty_per_db=1.0,
        feasible_vswr=1.5,
        objective="minimize post-match VSWR",
        elapsed_s=12.5,
    )
    spec = _spec(
        reflector="radials",
        reflector_spacing_wl=0.20,
        radial_droop_deg=45.0,
        optimization=opt,
    )
    restored = spec_from_dict(spec_to_dict(spec))
    assert restored == spec
    assert restored.optimization.input == base


def test_minimal_dict_uses_defaults():
    spec = spec_from_dict(
        {"freq_mhz": 436.0, "conductor": {"kind": "round", "diameter_mm": 3.0}}
    )
    assert spec.phasing == "self"
    assert spec.reflector == "none"
    assert spec.sense == "rhcp"
    assert spec.segments == DesignSpec(freq_mhz=1.0, conductor=spec.conductor).segments


def test_label_omitted_when_unset_present_when_set():
    assert "label" not in spec_to_dict(_spec())
    assert spec_to_dict(_spec(label="2 m"))["label"] == "2 m"


def test_notes_round_trip_and_omitted_when_unset():
    assert "notes" not in spec_to_dict(_spec())
    spec = _spec(notes="LEO sat pair, RHCP")
    assert spec_to_dict(spec)["notes"] == "LEO sat pair, RHCP"
    assert spec_from_dict(spec_to_dict(spec)) == spec


def test_json_single_object_round_trip():
    spec = _spec(label="2 m")
    specs = specs_from_json(specs_to_json([spec]))
    assert specs == [spec]


def test_json_list_round_trip():
    pair = [_spec(label="2 m"), _spec(freq_mhz=436.0, conductor=round_conductor(3.0))]
    assert specs_from_json(specs_to_json(pair)) == pair
