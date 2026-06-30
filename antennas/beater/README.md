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
and `conductor` are required; every other field defaults. The pipeline is
**spec -> optimized spec (optional) -> derived artifacts** (cut sheet, NEC deck,
plots), so every artifact reflects exactly the spec it was handed.

```
uv run beater designs/satellite_pair.json --sweep
echo '{"freq_mhz":145.9,"conductor":{"kind":"round","diameter_mm":5}}' | uv run beater -
# optimize the reflector, then bake the optimized spec to reuse it later
uv run beater my_design.json --optimize-reflector --emit-spec my_design.optimized.json
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
- `notes`: optional free-text design intent; carried through optimization.
- `optimization`: output-only provenance, written by `--optimize-reflector` (the
  input spec and the search parameters). You do not author it; it round-trips so
  an optimized spec records where it came from.

A JSON document may hold one spec object or a list of them; a list runs each
(and overlays them in plots).

### Actions

- `--optimize-reflector` search reflector radial count, spacing, and droop. A
  spec -> spec transform: it keeps the fewest radials that still meet the axial
  ratio and post-match VSWR objectives (for each count, a coordinate descent
  over spacing and droop finds the lowest-cost placement). The chosen geometry
  replaces the
  input's, and an `optimization` block records the input spec and search
  parameters.
- `--emit-spec <path>` write the resolved (optionally optimized) spec JSON to a
  file, or `-` for stdout -- this is how you bake an optimized design.
- `--emit-result <path>` write the derived cut list and performance as JSON to a
  file, or `-` for stdout; bandwidths are included when `--sweep` is also set.
  This is the machine-readable form of the cut sheet (`spec` plus a `build` and
  `performance` section), rendered from the same numbers as the text output.
- `--sweep` sweep frequency and report the 2:1 VSWR and 3 dB axial-ratio
  bandwidths of the matched antenna.
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

`--optimize-reflector` searches the reflector geometry to drive the feedpoint
resistance toward the transformer's sweet spot (about 112 ohm for 75 ohm coax),
minimizing post-match VSWR while keeping axial ratio under budget. It keeps the
fewest radials that still meet the objectives, since the radial count and the
best spacing/droop are coupled (a sparser screen shifts the optimum), so the
spacing and droop are re-searched for each candidate count.

`--sweep` holds the tuned physical antenna fixed, sweeps the analysis frequency,
and reports two bandwidths: the band where the matched VSWR stays under 2:1
(impedance bandwidth, with an idealized lossless match) and the band where the
boresight axial ratio stays under 3 dB (the usable circular-polarization
bandwidth, which is the narrower, and usually the binding, limit).

## Example: VHF/UHF satellite pair

A worked 2 m + 70 cm RHCP pair lives in `designs/`. `satellite_pair.input.json`
is the authored intent (bands, conductor, RHCP, radials; its `notes` field
states the objective, and reflector count/spacing/droop are left for the
optimizer). Optimizing it produces `satellite_pair.json`, the optimized spec
carrying its provenance; the rest derive from it.

```
# authored input -> optimized spec (provenance and notes carried through)
uv run beater designs/satellite_pair.input.json \
    --optimize-reflector --emit-spec designs/satellite_pair.json

# cut sheets and bandwidths for both bands
uv run beater designs/satellite_pair.json --sweep

# machine-readable cut list + performance (build, performance, bandwidth)
uv run beater designs/satellite_pair.json --sweep \
    --emit-result designs/satellite_pair.result.json

# performance-plot page (HTML)
uv run beater designs/satellite_pair.json --plot designs/eggbeater-performance.html

# tuned NEC decks, one design at a time (--deck is single-design only)
jq '.[0]' designs/satellite_pair.json | uv run beater - --deck designs/eggbeater_2m.nec
jq '.[1]' designs/satellite_pair.json | uv run beater - --deck designs/eggbeater_70cm.nec
```

## Building

These notes apply to any eggbeater the tool produces; the per-design dimensions
are in the cut sheet (the text output or the `build` section of `--emit-result`).

- Each loop is a full-wave loop. The two loops mount in perpendicular vertical
  planes on a common vertical axis, fed at the bottom.
- Self phasing: the loops are paralleled at a single feedpoint. The larger loop
  is inductive and the smaller capacitive, so their currents fall ~90 degrees
  apart, producing circular polarization with no phasing harness.
- A radial reflector sits below the loops, its radials drooping below
  horizontal, with the loop centers a fraction of a wavelength above the hub.
- Cancel the small residual feedpoint reactance with the series element, then
  transform to 50 ohm with the quarter-wave coax section (e.g. 75 ohm RG-59 /
  RG-11; scale the length to your coax with `match_vf`).
- Sense (RHCP vs LHCP) is set by which loop is large vs. small and how the feed
  is wired; mirror the loop assignment to swap handedness.

## Modeling caveats

- The match-network bandwidth assumes an idealized lossless network; treat the
  axial-ratio band as the operational coverage.
- Patterns are modeled with perfect conductors over a perfect (or simple)
  ground.
- Figures of merit are sampled over one azimuth quadrant (phi 0-90 deg), which
  assumes 90 degree symmetry. The crossed loops have it; an odd radial count
  (e.g. 3) does not, so confirm the azimuth ripple over a full sweep before
  committing to one. (A spot check on the 3-radial satellite pair found the
  effect benign near zenith.)

## Development

```
uv run ruff check
uv run ruff format
uv run pytest
```

Tests that drive `nec2c` are skipped automatically when it is not installed.
