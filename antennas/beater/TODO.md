# TODO

Optional work; nothing here blocks the current deliverable (JSON-driven
tool, both phasing schemes, round/bar conductor, reflector optimizer with
provenance, 4-chart HTML page, cut sheets, bandwidth sweeps, tuned NEC
decks, design doc, tests passing).

## Optimizer

- [ ] Replace fixed grid search in `optimize_reflector` with coordinate
      descent over the two continuous params (spacing, droop). The cost
      surface is smooth and unimodal; post-match VSWR is flattened by the
      quarter-wave transformer, so axial ratio dominates. Golden-section
      per axis (reuse the self-phase-delta routine), 2-3 alternating
      sweeps. Gives finer resolution than the 6x8 grid (48 NEC runs/band)
      in fewer runs, and stops selecting grid-edge values.
      `Optimization` provenance would record the search method and
      tolerances instead of the grids.
- [ ] Optimize radial count. Fewer radials is better (cheaper, lighter,
      less wind load); find the smallest count that still meets the AR and
      VSWR objectives. Add radial_count to the search, or sweep it as an
      outer loop and pick the minimum count within tolerance.

## Modeling fidelity

- [ ] Line phasing via NEC TL card. Today line phasing injects a phase at
      the source rather than modeling a real quarter-wave line; a TL-card
      harness would capture line loss and dispersion.
- [ ] Conductor loss and real ground. NEC runs are perfect-conductor with
      perfect or simple ground.

## Figures of merit

- [ ] Gain-coverage FoM. We report AR and VSWR but not realized gain over
      the coverage cone (e.g. minimum gain at theta=60 deg), which is what
      predicts pass performance.

## Geometry

- [ ] Square and other loop shapes; only circular loops today.
