# TODO

Optional work; nothing here blocks the current deliverable (JSON-driven
tool, both phasing schemes, round/bar conductor, reflector optimizer with
provenance, 4-chart HTML page, cut sheets, bandwidth sweeps, tuned NEC
decks, design doc, tests passing).

## Optimizer

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

## Plots and visualization

- [ ] Azimuth-elevation plots. The current charts are 1-D cuts (vs frequency,
      vs elevation on one plane). Add a 2-D az-el map (gain and/or axial ratio
      over the full hemisphere, e.g. a polar or contour heatmap) so azimuth
      asymmetry is visible -- especially useful for odd radial counts that break
      the phi 0-90 deg symmetry. Pairs with the full-azimuth FoM item.
- [ ] 3-D view of the NEC geometry. Render the wire model (both crossed loops
      plus the reflector radials) as an interactive or static 3-D plot from the
      same Wire data the deck is built from, so the physical structure -- loop
      shape, droop, spacing, feed location -- is visible without opening the
      deck in xnec2c. Drive it off the geometry module's Wire tuples (tag,
      endpoints, radius), not by re-parsing the .nec file. The plot page is
      currently body-only HTML with inline SVG and no CDN/JS dependencies, so
      either keep that rule with a few fixed SVG projections (XY top, XZ/YZ
      side, plus one isometric) or add a self-contained Canvas/WebGL viewer if
      rotate/zoom is wanted; decide before building. Make legible the feed
      segment at the bottom of each loop, the perpendicular XZ/YZ loop planes,
      the reflector droop and radial count, and the loop-center height above
      the hub.
