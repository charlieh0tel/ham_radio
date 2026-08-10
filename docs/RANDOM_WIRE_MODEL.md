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

The page ships a single line today, open at the far end:

    Zin  = Z0 * coth(gamma * l)
    gamma = alpha + j*beta
    Z0   = 60 * (ln(2l/a) - 1)      # Schelkunoff, thin wire
    beta = 2*pi/lambda * velocityFactor

The fitted replacement is two such lines in series at the feedpoint, the
antenna and the return path, which is the form finding 7 licenses:

    Zin = Za(l) + Zr(h + ret)
    Za  = ka * Z0(l)       * coth((alpha_a + j*beta_a) * l)
    Zr  = kr * Z0(h + ret) * coth((alpha_r + j*beta_r) * (h + ret))

`ka` and `kr` scale each line's Schelkunoff `Z0`, which is an average
over an isolated wire in free space and reads high once ground is
present.  `alpha` is carried in nepers per wavelength so one number
serves every band.

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
| `ka`, `kr` | fitted | `Z0` scales; ground lowers it, both near 0.75 |
| `alpha_a`, `alpha_r` | fitted | nepers per wavelength, loss and radiation |
| `beta_a`, `beta_r` | fitted | not assumed from a velocity factor |
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

NEC, offline, once.  It does not belong in the *scoring loop*: it models
the environmental unknowns only if told what they are, and assumed
values yield a precise answer to a question nobody asked -- the error
bar does not shrink, it hides behind more decimals.  The cost is real
too, sweeping every candidate length by band by frequency step in a
single-file Pages document.

That objection does not reach a different idea: one NEC run on demand,
after the user has chosen a length, against the height, return path and
soil they have already entered.  That is bounded work on a geometry the
user has described, and it checks the installation rather than the
envelope, which is exactly where this model is weakest.  Worth doing.

The obstacle there is licensing, and it is the reverse of the case in
`nec/random_wire/README.md`.  Those scripts are fine because they import
PyNEC and never ship it.  A wasm nec2c inside `docs/` would be
*distributing* GPL object code from an MIT repo, which obliges a
corresponding source offer under GPL and plausibly makes the page a
combined work covered by GPLv3 rather than MIT.  Loading it from a
separate file does not clearly escape that; it is the classic unsettled
boundary.  Decide the licence before building: either the NEC-enabled
page is explicitly GPLv3 with its own notice, or the engine has to be
permissively licensed.

So NEC is a calibration and validation instrument.  **What reaches the
page is constants and caveat text, never code.**

The modeller itself lives in `nec/random_wire/`.  An earlier draft of
this note had it staying outside the repo on licence grounds, which
confused two separate things.  PyNEC is GPL-3.0-only and is a declared
PyPI dependency, not vendored; MIT is GPL-compatible, so MIT scripts
that import it are fine to distribute, and nothing here copies PyNEC or
nec2c source.  Separately, and still true, a program's numeric output is
not covered by the producing program's licence, so the fitted constants
carry no obligation into the page.

Keeping it in the repo is the point rather than a concession.  The
page's claim to be defensible rests on constants with stated assumptions
and a bounded error; constants whose producing code has been discarded
cannot be checked by anyone.

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

Measured, H1 holds: see finding 7.  Note that the swamping in finding 4
is *evidence for* additivity rather than against it.  When `Zr`
dominates `Za`, their sum is `Zr`, which is exactly the flat
antenna-length dependence observed.  An earlier draft of this note had
that backwards.

## What NEC measured

First results, 2026-08-09.  Instrument as above, in `nec/random_wire/`.
Driver validated against textbook cases before anything else -- a
quarter-wave monopole over perfect ground reads 39.5+j22.7 against
~36+j21, a free-space half-wave dipole 79.1+j45.2 against ~73+j42, both
overshooting in the direction thin-wire segmentation predicts.

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

7. **The return path is additive, to about 20 percent.**  From the full
   sweep, 106848 points over 4 frequencies, 8 heights, 7 return lengths,
   3 soils and 159 lengths from 0.05 to 4 wavelengths, with no failed
   solves.  Testing H1 across 72 combinations of frequency, height, soil
   and return-length pair, the scatter of `Zin(ret_b) - Zin(ret_a)`
   across antenna length, relative to the size of that difference:

   | | residual |
   |---|---|
   | median | 0.20 |
   | under 0.35 | 89 percent of cases |
   | over 0.5 | 6 percent of cases |

   So the return path earns a separate additive term, and the antenna
   and the return can be fitted independently.  The residual is
   uniform with height in the typical case -- median 0.17 at 10 m, 0.18
   at 20 m, 0.22 at 3 m -- but its tail is entirely at low height, where
   it reaches 0.89 against 0.25 for `h >= 10 m`.  Mutual coupling
   between the wire and its return is what H1 neglects, and that is
   strongest when the two are close together.  A coupling correction
   growing as `h/lambda` falls is the shape to fit.

The structural lesson under the first six is the geometry section above:
feedpoint impedance is set by the whole conductor geometry, not the
antenna wire alone.  Finding 7 says that geometry decomposes, which is
what makes it tractable.

## Fit results

First fit, `nec/random_wire/fit.py`, over 96 groups of frequency by
height by soil, each holding 159 lengths by 7 return lengths.  Residuals
are taken on the complex logarithm: `|Zin|` spans tens of ohms to
kilohms across a sweep, so an absolute residual would fit the peaks and
ignore everything else, while a log residual is relative in magnitude
and plain angular error in phase, which is what SWR responds to.

| | magnitude error | phase |
|---|---|---|
| median | x1.22 | 10-16 deg |
| 90th percentile | x1.32 | |
| worst | x2.29 | 64 deg |

Each line carries a scale `ka` or `kr` on its Schelkunoff `Z0`.
Schelkunoff's figure is an average over an isolated wire in free space,
and over ground the image lowers it; both scales come out near 0.75,
which is that effect.  Adding `ka` alone took the median from x1.28 to
x1.22 and the 90th percentile from x1.39 to x1.32.

Tried and rejected: a susceptance terminating the open end, standing for
end effect.  It fitted to zero in every group (median 0.000, largest
0.004) and changed no error figure in the fourth decimal.  The five
parameter model is nested inside that seven parameter one, so the
comparison was fair, and end effect is simply not what the model was
missing.  Dropped rather than kept at zero.

Fitted values, with `alpha` in nepers per wavelength.  Per metre it came
out proportional to frequency, which is only the statement that a wire
loses a fixed fraction of its power per wavelength; per wavelength the
numbers are comparable across bands, which is what an interpolable
coefficient surface needs.

| parameter | median | range |
|---|---|---|
| `alpha_a` | 0.100 | 0.038 - 0.568 |
| `vf_a` | 1.000 | capped, see below |
| `ka` | 0.791 | 0.612 - 1.473 |
| `alpha_r` | 0.477 | 0.015 - 3.000 |
| `vf_r` | 0.934 | 0.589 - 1.150 |
| `kr` | 0.733 | 0.425 - 1.189 |

Three things worth drawing out.

**The antenna's velocity factor wants to be 1.0, not 0.95.**  Left free,
`vf_a` fitted to 1.003 and drifted as high as 1.018.  That is not a wave
outrunning light.  `vf_a` is a parameter of an equivalent line standing
in for a radiating structure, and `beta` absorbs what the line form
omits: `Z0` varies along a real wire where Schelkunoff's figure is an
average, the open end is capacitively loaded, and the thing radiates.
Capped at unity it costs 0.5 percent of median accuracy, and 75 percent
of groups then sit against the bound -- so read the result as "1.0 or a
little above", not as a measured phase velocity.

What survives is the direction, which is the part that matters for the
page: the wire is not propagating at 0.95.  The apparent shortening that
0.95 was standing for is the return path in series plus `Z0` varying
with length, both of which this model now carries explicitly.  That is
the quantitative form of the argument that velocity factor is emergent
rather than physical -- model the geometry and it goes away.

That 75 percent of groups press against the cap is itself a signal: a
rail-pinned parameter usually means the model form is missing something,
here most likely the end effect and the length dependence of `Z0`.

**The return path is about three times lossier than the antenna**,
`alpha_r` 0.405 against `alpha_a` 0.126, and its characteristic
impedance is about three quarters of the free-space thin-wire figure
(`kr` 0.741).  Both are what a wire lying along lossy ground should do.

**The error is flat with height, but its tail is not.**  Median error
sits between x1.23 and x1.31 at every height.  The worst cases are all
at low height -- x2.33, x2.25 and x2.19 at 2, 3 and 5 m, against x1.40
or better everywhere at 7 m and above -- and specifically at low
`h/lambda`, the worst being 1.9 MHz over poor ground where a 2 m height
is 0.013 wavelengths.  This is exactly the mutual coupling finding 7
predicted the additive model would neglect, and it is the term still to
add.

Known degeneracy, largely closed.  Before the velocity factors were
capped, `alpha_r` ran to its bound at 28.85 MHz above 20 m while `vf_r`
pinned at 1.15 or fell to 0.59: past roughly 3 nepers per wavelength
`coth` saturates, the return stops behaving as a line, and the fit uses
it as a lumped constant, which fits the data while meaning nothing.
Capping removed that escape route.  Parameters now sitting against a
bound, over 96 groups:

| parameter | at bound |
|---|---|
| `alpha_a` | 0 percent |
| `kr` | 0 percent |
| `alpha_r` | 8 percent |
| `vf_r` | 15 percent |
| `vf_a` | 78 percent, by construction |

The `alpha_r` and `vf_r` corners are still not measurements and should
not be read as any.

## Error bound

The bound the caveat text should carry.  Taken over 96 groups, each
fitted across 159 lengths and 7 return lengths.

Two numbers, and the second is the one the page may claim.  Fitting
coefficients independently for every frequency, height and soil gives
x1.35 worst case for `h/lambda >= 0.05`.  The page cannot do that: it
carries a small table and interpolates.  Measured with the tabulated
coefficients over the whole sweep, that costs almost nothing.

**Tabulated, for `h/lambda >= 0.05`: `|Z|` within x1.40 worst case,
x1.35 at the 90th percentile, x1.27 median.**  That covers 81 of the 96
groups and every soil.

The page quotes x1.5 rather than x1.40, because that figure is measured
against the sweep's own four frequencies while the page evaluates at
nine bands.  Checked at five frequencies the fit never saw -- 3.75,
10.125, 18.118, 21.225 and 24.94 MHz -- the tabulated model runs to
x1.47, median x1.30.  Interpolating across bands costs something, and
the quoted bound has to cover the bands a user actually picks rather
than the ones the sweep happened to sample.

| | per-group fit | tabulated, as shipped |
|---|---|---|
| median | x1.22 | x1.27 |
| 90th percentile | x1.28 | x1.35 |
| worst | x1.35 | x1.40 |

What `h/lambda >= 0.05` means in practice, since the user sets height in
feet and not wavelengths:

| band | height above which the bound holds |
|---|---|
| 160 m | 26 ft |
| 80 m | 13 ft |
| 40 m | 7 ft |
| 20 m and up | 4 ft or less |

**Below `h/lambda = 0.05` the bound degrades to x2.9 tabulated, x2.3
per-group.**  In practice that is 160 m and 80 m with a low wire.  It is not a region to refuse to
answer in, but it is one where the number on screen should be visibly
hedged.

**The bound survives conductor gauge.**  The main sweep ran entirely at
#14, so `a/lambda` was the one planned axis never executed and the
coefficients had seen a single diameter.  `gauge_sweep.py` and
`gauge_check.py` close that: 22896 further solves over #12, #14, #18 and
#22, a factor of 3.2 in diameter.

Agreement, which is the question the page cares about -- the shipped
#14 table used unchanged against each gauge:

| gauge | radius mm | median | 90th | worst |
|---|---|---|---|---|
| 12 | 1.026 | x1.27 | x1.34 | x1.41 |
| 14 | 0.814 | x1.26 | x1.33 | x1.39 |
| 18 | 0.512 | x1.26 | x1.34 | x1.40 |
| 22 | 0.322 | x1.27 | x1.36 | x1.44 |

Off-gauge is indistinguishable from #14's own x1.39.  Dependence
explains why: refitting per gauge moves the coefficients only slightly
and monotonically -- `alpha_a` 0.105 to 0.096 across the whole range,
`ka` 0.764 to 0.787, `alpha_r` 0.604 to 0.505, `kr` 0.726 to 0.748 --
because Schelkunoff's `Z0` already carries the dominant `log(radius)`
term, leaving the fitted scales little to absorb.

`vf_a` fits to 1.0000 at every gauge, which also disposes of the idea
that wire thickness was behind it.

Tested at medium soil on a reduced grid, three heights by three return
lengths, since one axis was the question rather than the whole surface.

Two hypotheses were tried against that low region and both failed, which
is worth recording so they are not tried again:

- **End effect**, a susceptance terminating the open end.  Fitted to
  zero in all 96 groups, largest 0.004.
- **A height-dependent `Z0`**, blending Schelkunoff's isolated-wire
  figure with the wire-over-image value `60 ln(2h/a)` by an effective
  length, on the theory that whichever return conductor is nearer sets
  `Z0`.  Median x1.220 against x1.225, low region x1.272 against x1.295,
  and the worst case got *worse*.  A wash.

The residual that remains is structured in antenna length rather than
return length -- flat against return length, but running from +1.09 in
log magnitude at short lengths to -0.57 at three wavelengths, with an
oscillation peaking near the odd quarter waves.  So it is not the mutual
coupling finding 7 predicted; that attribution was wrong.  Something in
how loss scales with length is still unmodelled.

Chasing it further is not obviously worth it.  The remaining error lives
in six groups at `h/lambda < 0.02`, which is 160 m with a wire 6 to 16 ft
up over poor soil -- a marginal antenna whose real behaviour is
dominated by the installation variance this model already refuses to
predict.  x1.22 median is comfortably inside the severalfold spread that
height, counterpoise and common-mode current impose on a real
installation.

## What it does to the recommendations

Swapping the model moved the picks a long way, which is the change worth
checking hardest since recommending lengths is the whole job.  At the
page's defaults -- 30 ft up, 25 ft of return, medium soil, 9:1, the
80/40/20/15/10 band set:

| old model | new model |
|---|---|
| 180.0 ft (SWR 1.59) | 80.5 ft (2.02) |
| 169.1 ft (1.61) | 151.2 ft (2.38) |
| 116.3 ft (2.00) | 180.1 ft (2.93) |
| 99.9 ft (2.09) | 195.2 ft (2.99) |
| 89.9 ft (2.22) | 110.4 ft (3.56) |
| 78.1 ft (2.28) | 126.5 ft (4.19) |

Agreement with the published tables improved: the median gap from a pick
to a published length falls from 6.5 ft to 5.5 ft, and picks landing
within 5 ft go from 1 in 6 to 3 in 6.  The new model is also uniformly
less optimistic, best score 2.02 against 1.59, which is what adding a
lossy return path should do.

But it rates two staples badly -- 71 ft at 6.56 where the old model said
2.72, and 119 ft at 4.44 against 2.03 -- so both were checked against
NEC directly rather than trusted.  **NEC agrees with the model**, and
the two lengths fail for entirely different reasons.

**71 ft is a velocity-factor casualty.**  NEC gives it SWR 10.9 on 40 m
and 5.6 on 20 m at the default site.  A published table dodges
`n * lambda/2` computed at vf 0.95, which puts the 40 m half wave at
65.3 ft and leaves 71 ft 8.7 percent clear.  The fitted antenna line
runs at 1.00, putting it at 68.8 ft and leaving 71 ft 3.2 percent clear;
on 20 m the second half wave moves from 15.4 percent clear to 4.6.  So
71 ft sits on the shoulder of a resonance on two bands at once, and the
published tables miss it because they assume a wire slower than the one
NEC models.

That generalises uncomfortably: if the effective velocity factor is
nearer 1.00 than 0.95, the published lengths are systematically placed
against resonances about 5 percent too short.  Stated carefully, `vf_a`
is a parameter of the antenna line inside a two-line model, not a
directly measured wave speed -- but NEC confirms the behaviour it
predicts at 71 ft without reference to the fit.

Checked for a published refutation of 71 ft, and there is none.  The
only documented criticism of the source list is James KB5YN catching
that VE3EED's original table called 220 ft good when it is the tenth
half-wave multiple on 15 m; VE3EED accepted it and recomputed out to
500 ft.  That is an arithmetic slip inside the method, not a challenge
to it.

The nearest independent corroboration is J.C. Sprott's technote, which
runs the same avoid-the-resonances search from scratch and arrives at
74 ft excluding 160 m, never mentioning 71.  That is 4 percent off the
staple in the same direction as this model, and 74 ft is what this
page's classical mode already picks for that band set.  Sprott also
treats the feedline as part of the electrical length, which is finding 4
in print years earlier, and handles velocity factor explicitly, which is
the parameter the 71 ft result turns on.

Cutting the other way, Ham Radio Outside the Box measured an 84 ft wire
at 21-307 ohms across the bands, challenging the 450 ohm and 9:1
convention rather than the lengths.  Those figures are lower than this
model or NEC gives and sit against finding 2, though a commenter
attributed them to the 3 ft coax jumper used, and the piece reports no
height, counterpoise or modelling.

So the 71 ft result here is novel rather than a restatement of known
criticism, which is a reason to hold it more loosely, not less: it rests
on one sweep with an unswept return height worth up to 4.6x and
segmentation unconverged at 13 percent.

The 25 ft return default was the obvious suspect for the 71 ft verdict,
and it is not the cause.  Scored across return runs from 10 to 130 ft at
the default height, 71 ft reads 7.4, 6.6, 7.5, 6.5, 5.9 and 5.6: bad at
every one of them, and worst nowhere near the default.  The verdict is
robust to the parameter most likely to have produced it.

Two things did come out of that check.  Most published lengths improve
with a longer return -- 29 ft goes 4.5 to 2.4, 41 ft goes 3.7 to 2.0,
107 ft goes 3.8 to 2.4 -- which supports the ARRL's quarter-wave
counterpoise advice against this page's 25 ft default.  And with a long
return the whole curve flattens: at 130 ft every offered length scores
between 2.1 and 2.3, where at 25 ft they spread 2.0 to 3.6.  **Get the
counterpoise right and the wire length matters less**, which is arguably
the more useful advice than any particular length.

Against changing the default: 25 ft gives the best agreement with the
published tables of any return length tried, median gap 3.5 ft against
5.1 to 9.5 elsewhere.  That looks like coincidence rather than a reason,
but it is worth knowing before moving it, and a typical user really does
just have their coax run.

**119 ft fails the other way.**  At vf 1.00 it is *more* clear of the
80 m half wave than at 0.95, 9.3 percent against 4.5, yet NEC still
gives SWR 13.6 there.  It is not near a half wave; it is carrying large
reactance, which a keep-out on `n * lambda/2` cannot see by
construction.  This is the "continuous cost instead of a binary
keep-out" gain, appearing in a real case.

84 ft checks out on both counts -- NEC 7.7 / 2.0 / 1.3 / 1.5 / 3.0 --
and the new model's best pick of 80.5 ft sits beside it.

## Known unchecked

Things the numbers above rest on that were never tested, kept here so
they are not mistaken for settled.

**Segmentation is not converged.**  Every solve used 20 segments per
wavelength, the usual accuracy rule, and that choice was never checked.
Against 80 segments per wavelength the same geometry moves 13 percent at
both a quarter and a half wave, 4 percent at one wavelength and 2
percent at two.  So the x1.5 bound is measured against NEC-at-20-
segments, not against converged NEC, and part of it is the discretisation
rather than the model.  Convergence is also not monotonic between 40 and
80, so the true figure is not simply "13 percent worse".

**The return conductor is the same wire as the antenna.**  Both take one
radius, so the gauge sweep moved them together.  A real coax shield is
nearer 8 mm than 0.8 mm, a factor of ten the sweep never explored, and
the return is the term the low-height error already lives in.

**The wire is horizontal.**  No slope, no inverted L, no sag, though a
sloper is at least as common as a flat top for a random wire.

**The classical mode still defaults to vf 0.95.**  The impedance mode's
71 ft result says that figure places the resonances about 5 percent too
short, so the two modes now disagree about which lengths are safe, and
the classical one agrees with the published tables partly by sharing
their assumption.  Changing its default would move every classical
recommendation and break agreement with tables the user can look up, so
it is a decision rather than a fix.

## The return path's geometry, measured

Two things about the return were fixed for the whole sweep and are
choices rather than measurements.  `geometry_check.py` puts numbers on
both, at the page's default site.

**Bearing barely matters.**  A counterpoise wire often runs out along
the antenna; a feedline acting as counterpoise usually heads away, at
anything from in line to square.  Across 0 to 180 degrees the feedpoint
moves 1.20x on 80 m and 1.07x or less on every other band.  The return
lies close to lossy ground, whose image largely cancels its coupling to
the elevated wire, so which way it points is nearly irrelevant.  All the
arrangements are real and the model does not need to choose between
them.

**Height matters more than anything else in the model.**  Raising the
return from 5 cm to 1-2 m moves the feedpoint by up to 4.6x on 20 m,
2.6x on 10 m, 2.3x on 15 m -- far outside the x1.5 bound, and larger
than height, soil or gauge.

| 84 ft, return height m | 0.01 | 0.05 | 0.25 | 1.0 | 2.0 |
|---|---|---|---|---|---|
| 20 m SWR | 1.7 | 1.3 | 2.4 | 4.1 | 6.2 |
| 10 m SWR | 3.3 | 3.0 | 2.6 | 3.8 | 6.6 |

The sweep's 5 cm stands for a feedline or counterpoise **lying on the
soil**, and 0.01 m gives nearly the same answer, so the assumption is
safe for that install -- which is the common one.  It is not safe in
general.  An elevated counterpoise, elevated radials, or a feedline on
standoffs is a different antenna, and the fitted coefficients say
nothing about it.

### Swept, and the model can absorb it

53424 further solves over seven return heights from 0.01 to 3 m,
`return_height_sweep.py`.  The degenerate case where the return sits at
the antenna's own height is skipped: it leaves no vertical drop, and it
is the only thing that failed.

Agreement first.  The shipped table, fitted at a 5 cm return, holds only
while the return stays near the ground:

| return height m | median | 90th | worst |
|---|---|---|---|
| 0.01 | x1.31 | x1.42 | x1.43 |
| 0.05 | x1.25 | x1.33 | x1.37 |
| 0.15 | x1.31 | x1.40 | x1.44 |
| 0.50 | x1.44 | x1.89 | x2.15 |
| 1.00 | x1.57 | x2.02 | x2.19 |
| 2.00 | x1.69 | x2.71 | **x4.15** |
| 3.00 | x1.86 | x2.21 | x2.85 |

So the x1.5 bound survives to about 15 cm and breaks past that, which
puts a number on "assumed to lie on the ground".

Dependence is the good news.  Refitted per return height the model
reaches x1.16 to x1.38, so it can describe every one of these, and the
parameters move exactly where the two-line decomposition says they
should:

| return height m | `alpha_a` | `ka` | `alpha_r` | `vf_r` | `kr` |
|---|---|---|---|---|---|
| 0.01 | 0.109 | 0.784 | 0.959 | 0.874 | 0.710 |
| 0.05 | 0.107 | 0.782 | 0.570 | 0.944 | 0.810 |
| 0.15 | 0.105 | 0.780 | 0.383 | 0.964 | 0.797 |
| 0.50 | 0.103 | 0.788 | 0.271 | 0.985 | 0.834 |
| 1.00 | 0.101 | 0.807 | 0.308 | 1.000 | 0.877 |
| 2.00 | 0.104 | 0.746 | 0.296 | 0.988 | 0.922 |
| 3.00 | 0.105 | 0.771 | 0.159 | 1.000 | 0.796 |

The antenna line does not notice: `alpha_a` stays near 0.10, `ka` near
0.78, `vf_a` exactly 1.0000 throughout.  Everything happens in the
return line, where lifting the wire off lossy ground drops `alpha_r`
sixfold and pulls `vf_r` up to unity as the ground stops loading it.
That is the decomposition earning its keep: a change to one conductor
shows up in that conductor's parameters and nowhere else.

That suggested return height was an axis to tabulate rather than a
caveat to carry.  The full sweep says otherwise, and the reason is worth
recording.

### Why it stays a caveat

228960 solves over soil by frequency by antenna height by return height
by return length, `unified_sweep.py`, then fitted per group.

First, the axis to index on is **return height in metres**, not
`rh/lambda`.  That breaks the dimensionless-ratio convention and does so
for a reason: the return lies over a lossy half-space, and the image sits
about a skin depth down, which is an absolute length.  In these soils
that is 0.5 to 11.5 m across HF, the same order as the return heights
themselves, so absolute height is what the return line feels.  The
fitted parameters agree, moving monotonically against metres while
`rh/lambda` barely separates them.

Second, and decisively, **the model form fails before the table does**.
Giving every group its own best-fit coefficients -- the most the two-line
form can possibly do -- the error grows with return height:

| return height m | median | 90th | worst |
|---|---|---|---|
| 0.01 | x1.20 | x1.31 | x2.20 |
| 0.05 | x1.20 | x1.32 | x2.10 |
| 0.15 | x1.20 | x1.31 | x2.09 |
| 0.50 | x1.24 | x1.31 | x2.02 |
| 1.00 | x1.34 | x1.43 | x2.00 |
| 2.00 | **x1.60** | **x2.20** | x2.42 |

A 2D table over `h/lambda` and return height was built and measured
anyway, 480 numbers against the present 120.  Below 15 cm it matches
what ships, median x1.27 and worst x1.44.  Above it, median x1.36 and
worst x4.30 -- worse than the low-`h/lambda` corner the page already
hedges.  Tabulating cannot beat the form it tabulates.

The physical reading is that the additive decomposition is what breaks.
H1 was measured at a return lying on the ground, where the image
cancels most of the coupling between the two conductors.  Lift the
return a metre or two and it becomes a radiator in its own right,
coupled to the antenna, and `Za + Zr` stops being the whole story --
which is the same mutual coupling the finding 7 residual tail pointed
at.

So the return stays assumed to lie on the ground, and that assumption
keeps its caveat rather than becoming a control.  Modelling an elevated
counterpoise needs a coupling term between the lines, not another axis
on the table.

## References

Sources for the published length tables this page is measured against,
and for the literature check on 71 ft.

- Jack Clarke VE3EED (SK), *The "Best" Random Wire Antenna Lengths*.
  The origin of the widely copied good/bad length tables.
  https://ve3ips.wordpress.com/2021/11/02/the-best-random-wire-antenna-lengthsrandom-wire-lengths-you-should-and-should-not-use-jack-ve3eed-sk/
  Mirrors: https://www.hamuniverse.com/randomwireantennalengths.html and
  https://ve7sar.blogspot.com/2019/01/the-best-random-wire-antenna-lengths.html
  The one documented correction to it is James KB5YN pointing out that
  220 ft was listed good while being the tenth half-wave multiple on
  15 m; VE3EED recomputed out to 500 ft in response.

- Mike Markowski AB3AP, *Random Wire Antenna Lengths*.
  https://udel.edu/~mm/ham/randomWire/
  The keep-out calculation this page's classical mode implements, and
  the origin of the C and Matlab versions in `random_wire/`.

- J.C. Sprott, *Optimal Length of Random Wire Antenna*, University of
  Wisconsin-Madison technote.
  https://sprott.physics.wisc.edu/technote/randwire.htm
  Independent run of the same avoid-the-resonances search, arriving at
  74 ft excluding 160 m and 143 ft for all bands.  Treats the feedline
  as part of the electrical length and handles velocity factor
  explicitly.

- *Random Wire Antennas -- A Challenge to Common Knowledge*, Ham Radio
  Outside the Box, 2024.
  https://hamradiooutsidethebox.ca/2024/09/04/random-wire-antennas-a-challenge-to-common-knowledge/
  Measures an 84 ft wire at 21-307 ohms and challenges the 450 ohm and
  9:1 convention rather than the lengths.

- ARRL, *Random Wires*.
  http://www.arrl.org/random-wires
  The ARRL's own guidance offers **no** recommended lengths at all, only
  that a shorter wire reaches fewer bands.  It does specify the
  counterpoise: a quarter wave at the lowest frequency in use, which is
  about 66 ft on 80 m and 130 ft on 160 m.  This page defaults the
  return path to 25 ft, far short of that, and the sweep shows return
  length matters a great deal -- worth revisiting.

- S.A. Schelkunoff, *Theory of Antennas of Arbitrary Size and Shape*,
  Proc. IRE 29(9), 1941.  Source of the average characteristic
  impedance `Z0 = 60 (ln(2l/a) - 1)` used for both lines.

Not searched: QST, QEX and the ARRL Antenna Compendium, which is where a
serious treatment of end-fed feedpoint impedance would more likely sit,
and where a real refutation of 71 ft would most likely be found.  The
literature check above covers amateur web sources only.

## What the model deliberately does not do

- Predict a specific installation's feedpoint impedance.
- Model common-mode current on the feedline shield.  With a poor return
  path, "the feedpoint impedance" is not a well-defined single number at
  all, whatever the model prints.
- Model sag, insulation, nearby structures, or coupling to house wiring.
- Claim accuracy better than the installation variance, which is the
  dominant term and is not modelled.
