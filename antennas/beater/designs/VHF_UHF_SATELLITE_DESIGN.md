# VHF/UHF satellite eggbeater pair

A 2 m and 70 cm eggbeater for LEO satellite work: circularly polarized,
omnidirectional in azimuth, with a drooping radial reflector tilting the pattern
upward to favor high-elevation passes.

## Objective

- Two antennas: 2 m (145.9 MHz) and 70 cm (436 MHz).
- Right-hand circular polarization (RHCP) on both bands.
- Axial ratio < 3 dB over the high-elevation coverage cone.
- VSWR < 1.5 at 50 ohm after the matching section.
- Self-phased crossed loops; radial reflector with count, spacing, and droop
  tuned for the best match (fewest radials that meet the objectives).
- Round tubing: 5 mm on 2 m, 3 mm on 70 cm.

## Results

Both bands meet the objective. The reflector optimizer settled on just 3 radials
on each band at 0.20 wl spacing, with a droop of 25 deg (2 m) / 50 deg (70 cm).
That pulls the feedpoint resistance to ~111-113 ohm: the sweet spot for a 75 ohm
quarter-wave transformer, giving a near-perfect post-match VSWR (~1.00-1.02).
Axial ratio stays near 1.3-1.6 dB at band center. Coverage gain (the worst-case
gain anywhere within 60 deg of zenith) stays near 0 dBi, so the high-elevation
sky is covered with no deep holes. Dropping from 8 radials to 3 left axial ratio
and match essentially unchanged in the model, for a lighter, lower-wind reflector.

| Quantity              | 2 m (145.9 MHz) | 70 cm (436 MHz) |
| --------------------- | --------------- | --------------- |
| Conductor             | 5 mm round      | 3 mm round      |
| Large loop perimeter  | 2318.7 mm       | 792.7 mm        |
| Large loop diameter   | 738.1 mm        | 252.3 mm        |
| Small loop perimeter  | 2000.6 mm       | 670.5 mm        |
| Small loop diameter   | 636.8 mm        | 213.4 mm        |
| Detune (delta)        | 7.36 %          | 8.35 %          |
| Radials               | 3 x 554.8 mm    | 3 x 185.7 mm    |
| Radial droop          | 25 deg          | 50 deg          |
| Loop-center height    | 0.20 wl, 411 mm | 0.20 wl, 137 mm |
| Feedpoint Z           | 112.9 - 13.4j   | 110.8 - 22.4j   |
| Series match element  | 15 nH inductor  | 8 nH inductor   |
| 1/4-wave transformer  | 75 ohm, 339 mm  | 75 ohm, 113.5 mm|
| Axial ratio (cone)    | 1.27 dB         | 1.56 dB         |
| Coverage gain (cone)  | 0.09 dBi        | 0.06 dBi        |
| Sense                 | RHCP            | RHCP            |

### Bandwidth

The matched 2:1 VSWR bandwidth is wide, but the usable bandwidth is set by
circular polarization (3 dB axial ratio), which is the narrower limit. Both
satellite segments (145.8-146.0 MHz and 435-438 MHz) fall inside the axial-ratio
band.

| Band                  | 2 m                      | 70 cm                    |
| --------------------- | ------------------------ | ------------------------ |
| 2:1 VSWR              | 137.1-160.5 MHz (16.0 %) | 392.4-479.6 MHz (20.0 %) |
| 3 dB axial ratio      | 142.6-148.8 MHz (4.3 %)  | 421.7-444.4 MHz (5.2 %)  |

The VSWR bandwidth assumes an idealized lossless match network; treat the
axial-ratio band as the operational coverage.

The figures of merit are sampled over one azimuth quadrant (phi 0-90 deg), which
assumes the antenna shares that 90 deg symmetry. The crossed loops do, but a
3-radial reflector does not. A full 360 deg check confirms this is benign where
it matters: within 20 deg of zenith the gain ripple is under 0.3 dB and axial
ratio stays under 3 dB at every azimuth, and the full-azimuth worst-case
coverage gain (-0.0 dBi) matches the quadrant value to a tenth of a dB. The
azimuth asymmetry only grows toward the horizon (theta >= 40 deg), which the
design does not weight.

## Build notes

- Each loop is a full-wave loop; the two loops mount in perpendicular vertical
  planes on a common vertical axis, fed at the bottom.
- The loops are paralleled at a single feedpoint. The larger loop is inductive
  and the smaller capacitive; their currents fall ~90 degrees apart, producing
  circular polarization with no phasing harness.
- The reflector is 3 radials drooping below horizontal (25 deg on 2 m, 50 deg on
  70 cm), with the loop centers 0.20 wavelength above the hub.
- Cancel the small residual feedpoint reactance with the series inductor, then
  transform to 50 ohm with the quarter-wave 75 ohm coax section (RG-59 / RG-11,
  VF 0.66 assumed; scale length to your coax VF with `--match-vf`).
- Sense is set by which loop is large vs. small (and how the feed is wired);
  mirror the loop assignment to swap RHCP/LHCP.

## Reproduce

Lineage: `satellite_pair.input.json` is the authored intent (bands, conductor,
RHCP, radials; reflector spacing/droop left at defaults). Optimizing it produces
`satellite_pair.json`, the optimized spec carrying its provenance (the input
spec and the search parameters). Artifacts derive from the optimized spec.

```
# authored input -> optimized spec (with provenance baked in)
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

The tuned NEC decks are `eggbeater_2m.nec` and `eggbeater_70cm.nec` in this
directory; open them in xnec2c to inspect patterns or sweep frequency.
