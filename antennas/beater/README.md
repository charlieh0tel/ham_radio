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

```
uv run beater --freq 145.9 --conductor round:3.0
uv run beater --freq 145.9 --conductor bar:12.7x3.2 --phasing line --reflector ground
```

### Options

- `--freq` design frequency in MHz (required).
- `--conductor` cross-section (required):
  - `round:<dia_mm>` round wire or tube.
  - `strip:<width_mm>` thin flat strip (equivalent radius = width / 4).
  - `bar:<width_mm>x<thick_mm>` rectangular bar stock (GMD equivalent radius).
- `--phasing` `self` (detuned big/small loops, no harness) or `line`
  (equal loops plus a quarter-wave coax phasing line). Default `self`.
- `--reflector` `none` (free space) or `ground` (perfect ground plane below).
- `--reflector-spacing` loop-center height above ground, wavelengths (default 0.25).
- `--coax-vf` velocity factor of the phasing-line coax (default 0.66).
- `--match-vf` velocity factor of the matching-section coax (default 0.66).
- `--segments` polygon sides per loop (default 36).
- `--deck` write the tuned NEC deck to a file.

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

The full-wave loop feedpoint runs about 100-130 ohms, so the cut sheet also
sizes a quarter-wave matching transformer (`Z0 = sqrt(50 * Rin)`) to 50 ohm and
suggests the nearest standard coax.

## Development

```
uv run ruff check
uv run ruff format
uv run pytest
```

Tests that drive `nec2c` are skipped automatically when it is not installed.
