# random-wire.html: the impedance model

How the page decides whether a wire length is any good, what the model
does and does not claim, and how its constants are obtained.

Task status and measured results live in `RANDOM_WIRE_TODO.md`; this
file is the approach.

## What the model is for

The page answers one question: given the bands you want, how long
should the wire be?  Both methods it offers are answers to that, and
neither is a prediction of what an antenna analyser will read at your
feedpoint.

- **Classic mode** keeps a percentage margin away from `n * lambda/2`.
  The half-wave points are bad because the feedpoint impedance spikes
  there, so this is a proxy for impedance with the impedance removed.
  Its virtue is that it is checkable arithmetic.
- **Impedance mode** models `|Zin|` directly and scores lengths by the
  SWR they present at the radio through the transformer.  Its virtue is
  that it is the actual criterion.  Its cost is that it is true only
  under assumptions the user cannot see, which is what the rest of this
  document is about.

The output is an **envelope, not a prediction**.  A real end-fed's
feedpoint impedance is dominated by height, ground, the return path,
common-mode current on the feedline, and sag.  Measured resonant peaks
vary severalfold from modelled ones.  Quoting `|Z|` to three figures
would be false precision, and the page's caveat text exists to say so.

## Conventions

Where the physics is scale invariant, parameterise by the dimensionless
ratios `l/lambda`, `a/lambda` and `h/lambda` rather than by absolute
size.  A wire is electrically the same antenna at 40 ft on 40 m as at
20 ft on 20 m, and the fitted coefficients should say so once instead of
twice.

Not everything here is scale invariant, which is why the sweep keeps
frequency as a real axis: soil enters through its complex permittivity,
`eps - j*sigma/(omega*eps0)`, which depends on frequency.

## The runtime model

The feedpoint is treated as a transmission line, open at the far end:

    Zin  = Z0 * coth(gamma * l)
    gamma = alpha + j*beta
    Z0   = 60 * (ln(2l/a) - 1)      # Schelkunoff, thin wire
    beta = 2*pi/lambda * velocityFactor

Choosing this form over anything learned is deliberate.  `Zin` has
near-poles at the half-wave resonances, and that pole structure *is* the
physics of the problem.  `coth` carries it exactly and for free.  What
remains -- `alpha`, and the corrections to `beta` -- is smooth and
low-dimensional, which is an interpolation problem.  A fitted analytic
form also extrapolates sanely, states its own assumptions, and can carry
a written error bound; none of which a black box does.  See
`RANDOM_WIRE_TODO.md` for the reasoning against a neural network.

### The anchor problem

The two ends of the model are not independent.  Pinning `Zin` at one
length forces the other end to about `Z0^2 / (2 R)`, so a single anchor
cannot make the model right at a quarter wave and a half wave at once.

The shipped anchor is the end-fed half wave at 2450 ohms, the figure a
49:1 transformer is wound for.  NEC has since confirmed that end and
demolished the other: there is no characteristic quarter-wave impedance
to anchor to, because the resonator is not the antenna wire alone.
Which leads to the geometry below.

## Geometry: the return path is part of the antenna

The single most consequential correction to the original model.  The
feedpoint impedance is set by the whole conductor geometry:

    feedpoint ---------------------------- far end (open)   height h
        |
        | vertical drop, length h
        |
        +========== return run =========== station          ground

The return path stands for either real installation: the coax shield
carrying common-mode current back to the station, or a counterpoise wire
thrown out along the ground.  It is not a passive reference.  It
radiates, it resonates on its own with a half-wavelength period in
(drop + run), and when that approaches a half wave it dominates the
feedpoint outright -- antenna length stops mattering.  A 25 ft coax run
is a half wave on 20 m, so this is the common case, not the exotic one.

## Parameters

Split by what the user can actually measure.

| quantity | role | note |
|---|---|---|
| wire length | user control | the answer being sought |
| height `h` | user control | the number people know |
| return length | user control | default 25 ft |
| soil type | user control | three standard soils |
| conductor diameter | user control | fixed at #14 AWG today |
| transformer ratio | user control | 1, 4, 9, 49, 64 |
| `Z0` | derived | Schelkunoff, from `a` and `l` |
| `alpha` | fitted | radiation and ground loss folded in |
| `beta` | fitted | not assumed from a velocity factor |
| velocity factor | derived | see below |

**Velocity factor is an output, not an input.**  It is not an
independent physical quantity: it is the emergent consequence of
conductor diameter, height, return path, insulation and sag.  It was a
user control only because none of those were modelled, making it the one
fudge factor absorbing all of them.  Once height and diameter are
explicit, leaving it settable would let the user set the same physical
effect twice.  `?vf=` is still read as an override so existing links
resolve, following the `len`/`len_m` precedent.

Soil is exposed but must not be labelled as if it were a quality axis.
"Better" ground does not mean a better match: it means a sharper
resonance, deeper minima and higher peaks.  Permittivity shifts the
effective electrical length while conductivity damps, and the two do not
co-vary monotonically across the three standard soils.

## Where the constants come from

NEC, offline, once.  It does not belong at runtime: it models the
environmental unknowns only if told what they are, and a web
calculator's user cannot supply them.  Assumed values yield a precise
answer to a question nobody asked -- the error bar does not shrink, it
hides behind more decimals.  Cost is real too: wasm NEC in a single-file
Pages document, sweeping every candidate length by band by frequency
step.

So NEC is a calibration and validation instrument.  **Results ship as
constants and caveat text, never as code.**  That is also the licence
boundary: PyNEC and nec2c are GPL, this repo is MIT, and a program's
numeric output is not covered by the producing program's licence.  The
sweep scripts stay out of the repo.

### Method

1. Validate the driver against textbook cases before trusting it --
   quarter-wave monopole over perfect ground, free-space half-wave
   dipole.  Both should land within the overshoot thin-wire
   segmentation predicts.
2. Sweep the grid.  Antenna length is swept in wavelengths; height and
   return length are held in metres so every grid point is an
   installation someone could build.  Frequency is a real axis, for the
   reason under Conventions above.
3. Decide the fit form against the data before fitting to it.
4. Fit `alpha`, `beta` and a series loss term together, so both ends of
   the model land at once rather than one being forced by the other.
5. Bound the error across the parameter space.  That bound becomes the
   caveat on the plot, e.g. "within ~2x over 20-60 ft, 1-30 MHz,
   15-30 ft high".

### The decomposition hypothesis

Whether the return path earns a separate additive term is a structural
question, tested rather than assumed:

    H1:  Zin(l, ret) = Za(l) + Zr(ret)

the antenna and the return as two lines in series at the feedpoint.  If
H1 holds, the two fit independently and the return gets a clean additive
term -- the cheap, interpretable outcome.

It is falsifiable.  Under H1, `Zin(l, ret_b) - Zin(l, ret_a)` depends
only on the return lengths, so holding frequency, height and soil fixed
and sweeping antenna length should leave that difference constant.
Scatter comparable to the difference itself falsifies it and means the
two are coupled, in which case the return resonance must enter
multiplicatively or through the antenna's own `alpha`.

There is reason to doubt H1 in advance: when (drop + run) nears a half
wave, the return does not merely add to the feedpoint, it swamps it and
flattens the antenna-length dependence entirely.  Pure series addition
would not destroy the antenna's contribution that way.

## What NEC measured

First results, 2026-08-09.  Instrument as above: PyNEC, `uv`-managed
scratch scripts kept out of the repo.  Driver validated against textbook
cases before anything else -- quarter-wave monopole over perfect ground
reads 39.5+j22.7 against ~36+j21, free-space half-wave dipole 79.1+j45.2
against ~73+j42, both overshooting in the direction thin-wire
segmentation predicts.

All figures at 14.2 MHz, #14 AWG.

1. **The half-wave anchor holds.**  The page reads 2480+j0 at its own
   half wave against the 2450 anchor; NEC gives 2600-3100 for
   `h >= 10 m`, rising to 4800-6200 at `h = 5 m` with a short return.
   The anchor is 10-20 percent low and otherwise sound.

2. **The quarter-wave anchor is not a real quantity.**  NEC spans
   133-3500 ohms at a quarter-wave antenna wire depending on height,
   return length and ground.  The page's 52 ohms sits below almost
   every configuration measured.  Cause is definitional: the page's `l`
   is the antenna wire, but the resonator is `l` plus the drop plus the
   return.  Bonded to ground over average earth, a quarter-wave *top
   wire* reads 183 ohms at `h = 2 m`, 2193 ohms at `h = 5 m` (where the
   total reaches a half wave), and 69 ohms at `h = 10 m`.  Ground loss
   adds to it: a `lambda/4` inverted L reads 13.8 ohms over perfect
   ground and 142.8 ohms over average ground at `h = 2 m`.
   Consequence: the impedance mode's penalty on odd-quarter-wave
   lengths is substantially an artifact.

3. **Measured half-wave reactance is strongly inductive**, +j1200 to
   +j1500 at `h >= 10 m`, where the coth model gives j0 at its own
   resonance.  Systematic, and the reason `beta` has to be fitted
   rather than assumed from a velocity factor.

4. **The return path is a resonator in its own right.**  Sweeping
   return length alone at a fixed antenna wire, `|Z|` oscillates with a
   clean half-wavelength period in (drop + run), a factor of 2-3.5:

   | (drop+run)/lambda | 0.71 | 0.92 | 1.21 | 1.42 | 1.71 | 1.92 |
   |---|---|---|---|---|---|---|
   | `\|Z\|` at `lambda/4` | 173 | 546 | 265 | 462 | 296 | 422 |

   When (drop + run) approaches a half wave the return resonance
   dominates the feedpoint entirely and antenna length stops mattering:
   at `h = 5 m` with a 5 m return, `|Z|` is flat at 1800-3500 ohms
   across `l/lambda` from 0.05 to 0.40.  That is the failure mode where
   a user lengthens the wire and nothing improves.  A 15 m coax run is
   a half wave on 20 m, so this is common, not exotic.

5. **Height matters most below 10 m.**  Half-wave `|Z|` barely moves
   between 10 and 20 m (2674-3047) but reaches 3500-6200 at 5 m with a
   short return.

6. **Ground is not a single quality axis at low height.**  Sweeping
   `l/lambda` per ground type, the curves keep their shape and change
   level, so this is loss rather than a resonance shift -- but the
   ordering is not monotonic in "poor/average/good".  At `h = 3 m`
   better ground sharpens the resonance, giving the lowest minima (148
   against 305 for poor) and the highest peak (5480 against 4577).  At
   `h = 5 m`, average reads lowest across the whole range and good
   highest.  Permittivity shifts the effective electrical length while
   conductivity damps, and the two do not co-vary monotonically across
   the three standard soils.  Low heights are worth getting right:
   improvised wires of this sort get hung low.

The structural lesson under all six is the geometry section above:
feedpoint impedance is set by the whole conductor geometry, not the
antenna wire alone.

## What the model deliberately does not do

- Predict a specific installation's feedpoint impedance.
- Model common-mode current on the feedline shield.  With a poor return
  path, "the feedpoint impedance" is not a well-defined single number at
  all, whatever the model prints.
- Model sag, insulation, nearby structures, or coupling to house wiring.
- Claim accuracy better than the installation variance, which is the
  dominant term and is not modelled.
