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
