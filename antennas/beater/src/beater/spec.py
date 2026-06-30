"""JSON serialization for design specs.

The JSON form is the canonical representation; the CLI is sugar over it. Only
freq_mhz and conductor are required in a spec object -- every other field falls
back to the DesignSpec defaults. A JSON document may hold one spec object or a
list of them (for multi-design runs such as overlaid plots).

The runtime-only nec2c executable path is intentionally not serialized.
"""

import json

from .conductor import (
    KIND_BAR,
    KIND_ROUND,
    KIND_STRIP,
    Conductor,
    bar_conductor,
    round_conductor,
    strip_conductor,
)
from .design import DesignSpec, Optimization

# Optional spec fields carried in JSON, in a stable output order.
_OPTIONAL_FIELDS = (
    "phasing",
    "sense",
    "reflector",
    "reflector_spacing_wl",
    "coax_vf",
    "match_vf",
    "segments",
    "radial_count",
    "radial_length_wl",
    "radial_droop_deg",
    "label",
    "notes",
)


def conductor_to_dict(conductor: Conductor) -> dict:
    if conductor.kind == KIND_ROUND:
        return {"kind": KIND_ROUND, "diameter_mm": conductor.dimensions_mm[0]}
    if conductor.kind == KIND_STRIP:
        return {"kind": KIND_STRIP, "width_mm": conductor.dimensions_mm[0]}
    return {
        "kind": KIND_BAR,
        "width_mm": conductor.dimensions_mm[0],
        "thickness_mm": conductor.dimensions_mm[1],
    }


def conductor_from_dict(data: dict) -> Conductor:
    kind = data["kind"]
    if kind == KIND_ROUND:
        return round_conductor(float(data["diameter_mm"]))
    if kind == KIND_STRIP:
        return strip_conductor(float(data["width_mm"]))
    if kind == KIND_BAR:
        return bar_conductor(float(data["width_mm"]), float(data["thickness_mm"]))
    raise ValueError(f"unknown conductor kind: {kind!r}")


def optimization_to_dict(opt: Optimization) -> dict:
    return {
        "input": spec_to_dict(opt.input),
        "elapsed_s": opt.elapsed_s,
        "search": {
            "method": opt.method,
            "spacing_bounds_wl": list(opt.spacing_bounds_wl),
            "droop_bounds_deg": list(opt.droop_bounds_deg),
            "spacing_tolerance_wl": opt.spacing_tolerance_wl,
            "droop_tolerance_deg": opt.droop_tolerance_deg,
            "sweeps": opt.sweeps,
            "radial_count_grid": list(opt.radial_count_grid),
            "ar_target_db": opt.ar_target_db,
            "ar_penalty_per_db": opt.ar_penalty_per_db,
            "feasible_vswr": opt.feasible_vswr,
            "objective": opt.objective,
        },
    }


def optimization_from_dict(data: dict) -> Optimization:
    search = data["search"]
    return Optimization(
        input=spec_from_dict(data["input"]),
        method=search["method"],
        spacing_bounds_wl=tuple(search["spacing_bounds_wl"]),
        droop_bounds_deg=tuple(search["droop_bounds_deg"]),
        spacing_tolerance_wl=float(search["spacing_tolerance_wl"]),
        droop_tolerance_deg=float(search["droop_tolerance_deg"]),
        sweeps=int(search["sweeps"]),
        radial_count_grid=tuple(search["radial_count_grid"]),
        ar_target_db=float(search["ar_target_db"]),
        ar_penalty_per_db=float(search["ar_penalty_per_db"]),
        feasible_vswr=float(search["feasible_vswr"]),
        objective=search["objective"],
        elapsed_s=float(data["elapsed_s"]),
    )


def spec_to_dict(spec: DesignSpec) -> dict:
    """Serialize a spec; nullable fields (label, notes) and optimization are
    included only when set."""
    data = {
        "freq_mhz": spec.freq_mhz,
        "conductor": conductor_to_dict(spec.conductor),
    }
    for field in _OPTIONAL_FIELDS:
        value = getattr(spec, field)
        if value is None:
            continue
        data[field] = value
    if spec.optimization is not None:
        data["optimization"] = optimization_to_dict(spec.optimization)
    return data


def spec_from_dict(data: dict) -> DesignSpec:
    """Build a spec from a dict; missing fields use the DesignSpec defaults."""
    fields = {field: data[field] for field in _OPTIONAL_FIELDS if field in data}
    if "optimization" in data:
        fields["optimization"] = optimization_from_dict(data["optimization"])
    return DesignSpec(
        freq_mhz=float(data["freq_mhz"]),
        conductor=conductor_from_dict(data["conductor"]),
        **fields,
    )


def specs_from_json(text: str) -> list[DesignSpec]:
    """Parse one spec object or a list of them into a list of specs."""
    parsed = json.loads(text)
    if isinstance(parsed, list):
        return [spec_from_dict(item) for item in parsed]
    return [spec_from_dict(parsed)]


def specs_to_json(specs: list[DesignSpec]) -> str:
    """Serialize specs to JSON; a single spec becomes an object, not a list."""
    payload = [spec_to_dict(s) for s in specs]
    return json.dumps(payload[0] if len(payload) == 1 else payload, indent=2)
