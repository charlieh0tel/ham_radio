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
- [x] Optimize radial count. optimize_reflector now searches counts ascending
      and keeps the fewest meeting the AR and VSWR objectives (RADIAL_COUNT_GRID,
      FEASIBLE_VSWR), re-searching spacing/droop per count.
- [ ] (low priority) Full-azimuth figures of merit. The FoM grid samples only
      phi 0-90 deg, assuming 90 deg symmetry. Odd radial counts (e.g. 3) break
      it, but a one-time 360 deg check showed the effect is benign near zenith
      (gain ripple < 0.3 dB, AR < 3 dB within 20 deg of zenith; worst-case
      coverage gain matches the quadrant value to 0.1 dB). Only worth adding if a
      worst-case (not average) azimuth metric is wanted.

## Modeling fidelity

- [ ] Line phasing via NEC TL card. Today line phasing injects a phase at
      the source rather than modeling a real quarter-wave line; a TL-card
      harness would capture line loss and dispersion.
- [ ] Conductor loss and real ground. NEC runs are perfect-conductor with
      perfect or simple ground.

## Figures of merit

- [x] Gain-coverage FoM. Worst-case total gain over the coverage cone
      (theta <= 60 deg), reported in the cut sheet and the FoM table.

## Plots

- [ ] Azimuth-elevation plots. The current charts are 1-D cuts (vs frequency,
      vs elevation on one plane). Add a 2-D az-el map (gain and/or axial ratio
      over the full hemisphere, e.g. a polar or contour heatmap) so azimuth
      asymmetry is visible -- especially useful for odd radial counts that break
      the phi 0-90 deg symmetry. Pairs with the full-azimuth FoM item.

## Geometry

- [ ] Square and other loop shapes; only circular loops today.
