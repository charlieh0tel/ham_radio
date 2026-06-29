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


def test_spec_round_trip_bar_conductor():
    spec = _spec(conductor=bar_conductor(12.7, 3.2))
    assert spec_from_dict(spec_to_dict(spec)) == spec


def test_spec_round_trip_with_optimization():
    base = _spec()
    opt = Optimization(
        input=base,
        spacing_grid_wl=(0.20, 0.25, 0.30),
        droop_grid_deg=(0.0, 45.0),
        ar_target_db=3.0,
        ar_penalty_per_db=1.0,
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


def test_json_single_object_round_trip():
    spec = _spec(label="2 m")
    specs = specs_from_json(specs_to_json([spec]))
    assert specs == [spec]


def test_json_list_round_trip():
    pair = [_spec(label="2 m"), _spec(freq_mhz=436.0, conductor=round_conductor(3.0))]
    assert specs_from_json(specs_to_json(pair)) == pair
