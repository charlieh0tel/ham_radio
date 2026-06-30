# VHF/UHF satellite eggbeater pair

A 2 m and 70 cm eggbeater for LEO satellite work: circularly polarized,
omnidirectional in azimuth, with a drooping radial reflector tilting the pattern
upward to favor high-elevation passes.

## Objective

- Two antennas: 2 m (145.9 MHz) and 70 cm (436 MHz).
- Right-hand circular polarization (RHCP) on both bands.
- Axial ratio < 3 dB over the high-elevation coverage cone.
- VSWR < 1.5 at 50 ohm after the matching section.
- Self-phased crossed loops; 8-radial reflector with spacing and droop tuned
  for the best match.
- Round tubing: 5 mm on 2 m, 3 mm on 70 cm.

## Results

Both bands meet the objective. The reflector optimizer chose 0.20 wl spacing
and a droop of 40 deg (2 m) / 50 deg (70 cm), which pulls the feedpoint
resistance to ~112 ohm: the sweet spot for a 75 ohm quarter-wave transformer,
giving a near-perfect post-match VSWR (~1.01). Axial ratio stays near
1.3-1.6 dB at band center. Coverage gain (the worst-case gain anywhere within
60 deg of zenith) stays near 0 dBi, so the high-elevation sky is covered with no
deep holes.

| Quantity              | 2 m (145.9 MHz) | 70 cm (436 MHz) |
| --------------------- | --------------- | --------------- |
| Conductor             | 5 mm round      | 3 mm round      |
| Large loop perimeter  | 2318.4 mm       | 793.5 mm        |
| Large loop diameter   | 738.0 mm        | 252.6 mm        |
| Small loop perimeter  | 2007.1 mm       | 671.2 mm        |
| Small loop diameter   | 638.9 mm        | 213.6 mm        |
| Detune (delta)        | 7.20 %          | 8.35 %          |
| Radials               | 8 x 554.8 mm    | 8 x 185.7 mm    |
| Radial droop          | 40 deg          | 50 deg          |
| Loop-center height    | 0.20 wl, 411 mm | 0.20 wl, 137 mm |
| Feedpoint Z           | 112.7 - 16.4j   | 111.9 - 23.3j   |
| Series match element  | 18 nH inductor  | 9 nH inductor   |
| 1/4-wave transformer  | 75 ohm, 339 mm  | 75 ohm, 113.5 mm|
| Axial ratio (cone)    | 1.30 dB         | 1.62 dB         |
| Coverage gain (cone)  | 0.34 dBi        | 0.07 dBi        |
| Sense                 | RHCP            | RHCP            |

### Bandwidth

The matched 2:1 VSWR bandwidth is wide, but the usable bandwidth is set by
circular polarization (3 dB axial ratio), which is the narrower limit. Both
satellite segments (145.8-146.0 MHz and 435-438 MHz) fall inside the axial-ratio
band.

| Band                  | 2 m                      | 70 cm                    |
| --------------------- | ------------------------ | ------------------------ |
| 2:1 VSWR              | 132.9-160.5 MHz (18.9 %) | 392.4-479.6 MHz (20.0 %) |
| 3 dB axial ratio      | 141.8-148.6 MHz (4.7 %)  | 419.5-443.7 MHz (5.6 %)  |

The VSWR bandwidth assumes an idealized lossless match network; treat the
axial-ratio band as the operational coverage.

## Build notes

- Each loop is a full-wave loop; the two loops mount in perpendicular vertical
  planes on a common vertical axis, fed at the bottom.
- The loops are paralleled at a single feedpoint. The larger loop is inductive
  and the smaller capacitive; their currents fall ~90 degrees apart, producing
  circular polarization with no phasing harness.
- The reflector is 8 radials drooping below horizontal (40 deg on 2 m, 50 deg on
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

# performance-plot page (HTML)
uv run beater designs/satellite_pair.json --plot designs/eggbeater-performance.html

# tuned NEC decks, one design at a time (--deck is single-design only)
jq '.[0]' designs/satellite_pair.json | uv run beater - --deck designs/eggbeater_2m.nec
jq '.[1]' designs/satellite_pair.json | uv run beater - --deck designs/eggbeater_70cm.nec
```

The tuned NEC decks are `eggbeater_2m.nec` and `eggbeater_70cm.nec` in this
directory; open them in xnec2c to inspect patterns or sweep frequency.
