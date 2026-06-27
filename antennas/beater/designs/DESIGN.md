# VHF/UHF satellite eggbeater pair

A 2 m and 70 cm eggbeater for LEO satellite work: circularly polarized,
omnidirectional in azimuth, with a radial reflector tilting the pattern upward
to favor high-elevation passes.

## Objective

- Two antennas: 2 m (145.9 MHz) and 70 cm (436 MHz).
- Right-hand circular polarization (RHCP) on both bands.
- Axial ratio < 3 dB over the high-elevation coverage cone.
- VSWR < 1.5 at 50 ohm after the matching section.
- Self-phased crossed loops; 8-radial reflector, 0.25 wl below the loop centers.
- Round tubing: 5 mm on 2 m, 3 mm on 70 cm.

## Results

Both bands meet the objective (axial ratio ~1 dB, VSWR ~1.18 after a 75 ohm
quarter-wave match on the ~133 ohm feedpoint).

| Quantity              | 2 m (145.9 MHz) | 70 cm (436 MHz) |
| --------------------- | --------------- | --------------- |
| Conductor             | 5 mm round      | 3 mm round      |
| Large loop perimeter  | 2312.8 mm       | 788.2 mm        |
| Large loop diameter   | 736.2 mm        | 250.9 mm        |
| Small loop perimeter  | 1964.1 mm       | 651.4 mm        |
| Small loop diameter   | 625.2 mm        | 207.3 mm        |
| Detune (delta)        | 8.15 %          | 9.51 %          |
| Radials               | 8 x 554.8 mm    | 8 x 185.7 mm    |
| Loop-center height    | 513.7 mm        | 171.9 mm        |
| Feedpoint Z           | 133.4 - 14.4j   | 133.4 - 17.1j   |
| Series match element  | 16 nH inductor  | 6 nH inductor   |
| 1/4-wave transformer  | 75 ohm, 339 mm  | 75 ohm, 113.5 mm|
| Axial ratio (cone)    | 0.97 dB         | 1.01 dB         |
| Sense                 | RHCP            | RHCP            |

## Build notes

- Each loop is a full-wave loop; the two loops mount in perpendicular vertical
  planes on a common vertical axis, fed at the bottom.
- The loops are paralleled at a single feedpoint. The larger loop is inductive
  and the smaller capacitive; their currents fall ~90 degrees apart, producing
  circular polarization with no phasing harness.
- Cancel the small residual feedpoint reactance with the series inductor, then
  transform to 50 ohm with the quarter-wave 75 ohm coax section (RG-59 / RG-11,
  VF 0.66 assumed; scale length to your coax VF).
- The 1/4-wave transformer length assumes VF 0.66. For a different coax,
  regenerate with `--match-vf`.
- Sense is set by which loop is large vs. small (and how the feed is wired);
  mirror the loop assignment to swap RHCP/LHCP.

## Reproduce

```
uv run beater --freq 145.9 --conductor round:5.0 --reflector radials --sense rhcp --deck designs/eggbeater_2m.nec
uv run beater --freq 436   --conductor round:3.0 --reflector radials --sense rhcp --deck designs/eggbeater_70cm.nec
```

The tuned NEC decks are `eggbeater_2m.nec` and `eggbeater_70cm.nec` in this
directory; open them in xnec2c to inspect patterns or sweep frequency.
