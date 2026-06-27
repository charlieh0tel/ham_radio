# beater

Eggbeater antenna dimension generator with `nec2c` in the tuning loop.

An eggbeater is two full-wave loops in perpendicular vertical planes, fed in
phase quadrature to give a near-omnidirectional, circularly polarized pattern
with good high-angle coverage (popular for working LEO satellites). This tool
sets the geometry from closed-form formulas and then uses `nec2c` to tune
resonance and the 90 degree phasing, finishing with a physical cut sheet.

## Requirements

- `nec2c` on `PATH` (Debian/Ubuntu: `apt install nec2c`).
- `uv` for environment management.

## Usage

A design is a JSON spec, read from a file argument or stdin. Only `freq_mhz`
and `conductor` are required; every other field defaults.

```
uv run beater designs/satellite_pair.json --sweep
echo '{"freq_mhz":145.9,"conductor":{"kind":"round","diameter_mm":5}}' | uv run beater -
uv run beater my_design.json --optimize-reflector --deck my_design.nec
```

### Spec (JSON)

```json
{
  "freq_mhz": 145.9,
  "conductor": {"kind": "round", "diameter_mm": 5.0},
  "phasing": "self",
  "sense": "rhcp",
  "reflector": "radials",
  "reflector_spacing_wl": 0.20,
  "radial_count": 8,
  "radial_length_wl": 0.27,
  "radial_droop_deg": 45.0,
  "coax_vf": 0.66,
  "match_vf": 0.66,
  "segments": 36,
  "label": "2 m"
}
```

- `conductor` is `{"kind":"round","diameter_mm":d}`,
  `{"kind":"strip","width_mm":w}` (equiv radius = width / 4), or
  `{"kind":"bar","width_mm":w,"thickness_mm":t}` (GMD equiv radius).
- `phasing`: `self` (detuned big/small loops, no harness) or `line` (equal
  loops plus a quarter-wave coax phasing line). Default `self`.
- `sense`: `rhcp` or `lhcp` (default `rhcp`); verified against the NEC pattern.
- `reflector`: `none` (free space), `ground` (perfect ground plane), or
  `radials` (finite radial-wire reflector, ON6WG/M2 style).
- `reflector_spacing_wl`: loop-center height above the reflector (default 0.25).
- `radial_*`: count (8), length in wavelengths (0.27), droop in degrees (0).
- `coax_vf` / `match_vf`: phasing-line and matching-section velocity factors.
- `segments`: polygon sides per loop (default 36).
- `label`: optional name for output; defaults to none.

A JSON document may hold one spec object or a list of them; a list runs each
(and overlays them in plots).

### Actions

- `--sweep` sweep frequency and report the 2:1 VSWR and 3 dB axial-ratio
  bandwidths of the matched antenna.
- `--optimize-reflector` grid-search reflector spacing and droop for the lowest
  post-match VSWR (keeping axial ratio within budget).
- `--deck <path>` write the tuned NEC deck (single-design specs only).
- `--plot <path>` write a performance-plot page (HTML) for the design(s);
  multiple designs are overlaid.
- `--nec2c <path>` nec2c executable (default `nec2c`).

## How it works

Both phasing schemes use one model: two crossed loops, each driven by a
voltage source.

- `self`: equal feed phase; loop perimeters are detuned by +/- delta until the
  loop currents are 90 degrees apart (large loop inductive, small loop
  capacitive). The loops are paralleled at a common feedpoint.
- `line`: equal resonant loops, feed phases 0 and -90 degrees, modelling an
  ideal quarter-wave phasing line.

Conductor cross-sections are reduced to a NEC equivalent radius; the resonance
sweep then corrects for any residual error in that estimate.

The full-wave loop feedpoint runs about 100-130 ohms, so the cut sheet sizes a
match to 50 ohm: a series element (inductor or capacitor) to cancel any residual
feedpoint reactance, then a quarter-wave transformer (`Z0 = sqrt(50 * Rin)`)
with the nearest standard coax. The reactance is tuned out at the feed rather
than by resizing the loops, which would move the axial-ratio optimum.

`--optimize-reflector` grid-searches reflector spacing and droop to drive the
feedpoint resistance toward the transformer's sweet spot (about 112 ohm for
75 ohm coax), minimizing post-match VSWR while keeping axial ratio under budget.

`--sweep` holds the tuned physical antenna fixed, sweeps the analysis frequency,
and reports two bandwidths: the band where the matched VSWR stays under 2:1
(impedance bandwidth, with an idealized lossless match) and the band where the
boresight axial ratio stays under 3 dB (the usable circular-polarization
bandwidth, which is the narrower, and usually the binding, limit).

## Development

```
uv run ruff check
uv run ruff format
uv run pytest
```

Tests that drive `nec2c` are skipped automatically when it is not installed.
