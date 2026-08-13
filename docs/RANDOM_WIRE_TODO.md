# random-wire.html TODO

Task status and open decisions.  The modelling approach, the parameter
split, and what NEC measured are in `RANDOM_WIRE_MODEL.md`.

## Impedance-based length selection

Today the tool picks lengths by avoiding `n * lambda/2` with a fixed
percentage margin (AB3AP style).  That keep-out is a proxy: those
lengths are bad because the end-fed feedpoint impedance spikes there
(current node at the feed, `|Zin|` in the kilohms).  Selecting on
impedance directly is the same criterion with the proxy removed.

Potential gains:

- Continuous cost instead of a binary keep-out.  Rank candidate lengths
  by worst-case `|Zin|` (or post-unun SWR) across the selected bands.
- Catches the low-Z case.  Odd `lambda/4` gives ~35 ohm, which is ~4 ohm
  after a 9:1 unun.  The current model only avoids high-Z and is blind
  to this.  *Superseded:* NEC finding 2 measures 133-3500 ohm there, so
  the low-Z case is largely an artifact of ignoring the return path.
- Physically motivated zone widths.  The right margin scales with wire
  diameter and effective Q; a fixed percentage cannot express that.
- Better visual.  A predicted `|Z|` / SWR-vs-frequency trace for the
  recommended length beats keep-out bars for showing *why* a length is
  good.
- Makes the tuner a parameter: keep the match inside a stated range,
  e.g. `|Z|/9` within 25-600 ohm with bounded reactance.

Costs:

- Accuracy is worst exactly where it matters.  End-fed `Zin` is
  dominated by height, ground quality, counterpoise length, feedline
  common-mode current, and sag.  Real resonant peaks vary severalfold
  from predicted, so precise output would be false precision.
- Defensibility.  "Avoids half-wave resonance by 8%" is checkable
  arithmetic; "keeps `|Z|` under 1500 ohm" is true only under
  assumptions the user cannot see.
- Verification burden.  AGENTS.md wants math checked against
  references; `n * lambda/2` is trivially verifiable, an impedance
  model is not.

### Candidate model

Transmission-line approximation, open-circuited far end:

    Zin  = Z0 * coth(gamma * l),  gamma = alpha + j*beta
    Z0   = 60 * (ln(2l/a) - 1)    # Schelkunoff avg characteristic impedance
    beta = 2*pi/lambda * velocityFactor

Calibrate `alpha` so the model reproduces known anchors: `Zin ~ 36 ohm`
at `l = lambda/4`, which then yields `Z0^2/36` (several kilohms) at
`lambda/2`.  That gives a defensible envelope without pretending to
predict a specific installation.  Cheap enough for the browser, no new
dependencies.

### Status

Done: the page carries both methods behind a Method toggle (`?mode=`),
classical by default.  The default moved to impedance while that model
was being fitted and has moved back: the impedance mode carries an
EXPERIMENTAL ribbon.  Of the three reasons it went on, the first is now
gone -- the return height is swept and tabulated, and is a control --
while unconverged segmentation and a disagreement with the published
tables over staple lengths stand.  Neither geometry has been checked
against anything but NEC.  The impedance mode scores every
length by the geometric mean of the modelled SWR at the radio and
offers the local minima.  A worst-case score was tried first and
discarded: the lowest band always sets it, so it collapses into "prefer
the longest wire".

The model is anchored on the end-fed half wave at 2450 ohms, the figure
a 49:1 is wound for.  It was first anchored on the textbook 36 ohm
quarter-wave monopole, which assumes a perfect ground plane and put the
half wave near 5000 ohms, about twice what real antennas show; a 49:1
then read 1.7-2.2:1 where reality is near flat.  Re-anchored, the half
wave lands within 2 percent of target and a quarter wave falls at
44-70 ohms.

The half-wave end of that has since been confirmed against NEC; the
quarter-wave end has not survived it.  See the NEC findings below: a
quarter-wave antenna wire has no characteristic impedance to anchor to,
because the resonator includes the drop and the return path.

### Controls, decided

The model gained three parameters the user can actually measure --
height, return-path length and soil type -- and lost one they cannot,
the velocity factor.  All four shipped.  The velocity factor survives in
the classical mode only, where it is part of that method's checkable
arithmetic rather than a model parameter.

Once height and diameter are explicit, leaving `vf` settable would let
the user set the same physical effect twice and double-count it.

Dropped: a separate odd-`lambda/4` keep-out.  Measured, it empties the
solution space (HF-all returns nothing, the classic set drops to a
0.63 ft widest span), and the published tables sit *closer* to odd
quarter waves than chance because those points are the midpoints
between the half waves they avoid.  The impedance mode sees the low-Z
case as cost, which is the useful form of it.

## NEC: offline only, not in the loop

NEC does not belong at runtime.  It models the environmental unknowns
only if told what they are, and a web calculator's user cannot supply
them; assumed values yield a precise answer to a question nobody asked.
The error bar does not shrink, it just hides behind more decimals.
Cost is real: wasm NEC in a single-file Pages doc, sweeping every
candidate length x band x frequency step.

Use it instead as a one-time calibration and validation instrument.
Results ship as constants and caveat text, never as code.

Measured results are in `RANDOM_WIRE_MODEL.md`, under "What NEC
measured".  The findings referenced by number above and below live
there.

Remaining:

- [ ] **Ship the two geometries.**  Modelling is done and measured;
      what is left is the page.  Refined, for `h/lambda >= 0.05`:

      | | median | 90th | worst |
      |---|---|---|---|
      | flat top | x1.25 | x1.33 | x1.62 |
      | sloper | x1.15 | x1.21 | x1.27 |
      | shipped today | x1.25 | x1.32 | -- |

      So the flat top matches what is live while gaining counterpoise
      height as a real axis, and the sloper is better than either.
      Coefficients are in `nec/random_wire/coefficients2d.json`.

      Decided:

      - **Inline, stored sparsely.**  `alpha_a` and `ka` once per
        `h/lambda` node rather than repeated across every counterpoise
        node, which is 672 numbers instead of 960.  The page stays one
        self-contained file.
      - **New URL keys, old ones still read.**  `ret_m` means the whole
        return conductor and cannot keep that meaning, so the page
        writes the counterpoise run and height separately and still
        accepts `ret_m`, backing out the run on the assumption the
        counterpoise lay on the ground.  An old link resolves to the
        antenna it always meant, per the `len`/`len_m` precedent.
      - **Refuse unbuildable slopers.**  The wire must be longer than
        the rise from balun to apex, and the check is on the physical
        length rather than per band.  Say so, and say what length would
        reach, rather than modelling something that cannot be put up.
      - **Ribbon stays on both, text updated.**  Its first stated reason
        was an unswept return height, and that is now swept and
        tabulated.  The other two stand, and neither geometry has been
        checked against anything but NEC.

- [ ] **Slopers.**  Measured as not covered: against the flat model a
      sloper runs x1.57 to x5.72 median depending on which equivalent
      height is tried, and no substitution is consistent.  A common
      arrangement -- arguably the default, since the unun usually sits at
      the shack and the wire goes up to a tree.

      Remapping is out.  An effective height fits each case to x1.05-1.09
      median, so the form can represent a sloper, but the height it needs
      is frequency dependent (2.5 m at 7.15 MHz against 1.0 m at 14.175
      for the same antenna), and the page scores several bands at once.

      So it wants modelling, as a second geometry with its own table
      rather than another axis on this one.  A sloper's return really is
      different: the balun is already low, so there is almost no drop and
      the return is essentially just the counterpoise, where a flat top's
      return is dominated by the drop from h.  Same control, different
      line.

      The balun height needs no axis and no fixed value.  It looked
      like it did -- deviation up to x1.44 on 10 m across a stake-to-reach
      range -- but that measurement was confounded.  The balun height is
      the drop, the drop is part of the return conductor, and the model
      already solves the whole conductor analytically.  Holding the total
      return constant while moving the balun collapses the deviation to
      x1.08 worst, over every band and the whole range.

      So the page computes the return as `(balun height - counterpoise
      height) + run`, which is structurally what the flat top already
      does with wire height in place of balun height.  Nothing new is
      tabulated for it.

- [ ] **A sloper's wire has to be longer than the rise it climbs.**  Not
      a modelling choice but geometry: a wire from a 0.6 m balun to a
      20 m apex spans a 19.4 m rise, so nothing shorter reaches, and on
      10 m that rules out the entire length axis the page offers.  The
      page would have to refuse the combination rather than quietly
      model something unbuildable, and say why.

      That leaves the sloper with the same axes as the flat top: apex
      height, counterpoise height, counterpoise length, soil.  The sweep
      is `nec4_return_height_sweep.py` pointed at a sloper deck, and the
      page gains a geometry selector.

- [ ] **Counterpoise height as a control.**  Spiked and it works:
      `spike_return_height.py` fits NEC-4.2 across the axis from the
      ground to 0.9 of the wire height and the form holds, x1.13 to
      x1.19 median with only 0.9h degrading.  That reverses the earlier
      rejection, which was measured against PyNEC.

      Swept on the table's own axes and it holds: per-group error x1.19
      to x1.24 median from the ground to half the wire height, level with
      the shipped model's x1.25.  `alpha_r`'s bound is lowered and no
      longer rails.

      Only two of the six coefficients move along the axis, both
      monotonically -- `alpha_r` by x2.9 as the counterpoise sheds ground
      loss, `vf_r` from 0.82 towards 0.995 as it approaches free space.
      So what is left is:

      - decide the shape: a third table dimension, or a 1-D correction on
        `alpha_r` and `vf_r` against z/h.  The latter looks sufficient
        and is a far smaller change to the page.
      - fit it, ship the coefficients, and add the control
      - the model then has a regime where NEC-4.2 is measurably the
        better target, which is what would justify refitting on it

- [ ] Optional on-demand NEC run once a length is chosen, against the
      height, return path and soil already entered.  Different from the
      objection to runtime NEC, which was about sweeping every candidate:
      this is bounded work on a geometry the user has described, and it
      checks the installation rather than the envelope.

      `nec2c-wasm` and `nec2c-deck` now exist on npm (0.1.0, both
      GPL-3.0-or-later, both ours).  They split the licence question
      rather than answering it:

      - `nec2c-deck` builds decks and parses output, no solver and no
        dependencies.  It is our own code with no nec2c in it, so it can
        be relicensed at will; MIT would let the page use it freely.
      - `nec2c-wasm` is nec2c 1.3.1 compiled, so it carries Kyriazis's
        GPL and cannot be relicensed by us.  Serving it from `docs/` is
        distribution, and it makes the page a combined work.

      **Decided and done**: `docs/random-wire.html` is now
      GPL-3.0-or-later, with the notice in its header and the exception
      recorded in `LICENSE`.  The rest of the repository stays MIT.  The
      wasm loads from a CDN on click, as React and Babel already do, so
      the classical mode never fetches it.  `nec2c-wasm/inline` is the
      entry point to use, 361 KB in one file, which avoids serving a
      separate `.wasm` from Pages.

      **Blocked on a solver gap.**  `nec2c-deck`'s `buildDeck` takes
      `ground: boolean` and emits `GN 1`, a perfect ground plane.  This
      model is fitted against `GN 2`, the Sommerfeld solution, with real
      soil constants, and ground loss is what dominates at the low
      heights the page warns about.  A button built on `GN 1` would
      compare the model against a different problem and disagree for
      reasons the user cannot see, which is worse than no button.

      Two ways out, both small:

      - add ground constants to `nec2c-deck`, an optional `{eps, sigma}`
        that emits `GN 2` instead of `GN 1`; it is our package
      - have the page emit its own cards and use `nec2c-deck` only for
        `parseOutput`, which the package explicitly supports

      **Done in nec2c-deck 0.1.1**, which takes `{epsR, sigmaSm}` and
      emits `GN 2`.  Verified against the fixture, and it uncovered a
      deeper problem: see below.

      Ready for it: `nec/random_wire/reference_cases.json`, six
      installations with the feedpoint impedance PyNEC gives them across
      all five bands, generated by `reference_cases.py`.  The browser has
      to reproduce these within 2 percent before its output is worth
      showing anyone.  PyNEC wraps nec2++ and the page will carry
      Kyriazis's nec2c, so these are two independent translations of
      NEC-2 rather than the same code checking itself.

      The fixture is checked to discriminate: a deck built with `GN 1`
      instead of `GN 2` misses the reference by 5.3 to 36.9 percent, so
      the exact mistake that motivated it cannot pass.  The cases also
      span 329 to 3953 ohms and include the same length over poor and
      good ground, which differ by 11 percent, so a port that ignores
      soil constants fails too.

- [ ] **Decide what the browser check runs on.**  Was "blocked until
      nec2c is fixed"; that framing is dead, since the gap is the method
      and no upstream fix will close it.  Running `nec2c-wasm` would show
      the user a number about 30 percent high in exactly the
      configuration the page assumes, permanently.  Three ways out:

      - wait for a nec2++ wasm build; `nec2-js`'s `packages/necpp-wasm`
        has prebuilt wasm, a runner, bindings and tests, and nec2pp-wasm
        is reported in good shape, so this is the likely answer and the
        only option where both ends are right
      - move the offline fit to nec2c, so both ends share a solver and
        are wrong the same way -- cheap, and it discards the one
        implementation that passes the limit test
      - ship the button reporting a known implementation spread, which
        was defensible while "which is right" had no answer and reads as
        an excuse now that it does

      The measurement that decides it: run `sommerfeld.mjs` against the
      necpp-wasm runner and confirm it reproduces the nec2++ column
      rather than the nec2c one.  Small job.  See
      `nec/random_wire/HANDOFF-nec2js.md` -- currently held.

- [ ] **Model the counterpoise in contact with the ground.**  Most
      people let the coax lie on the dirt.  The model holds it 5 cm up
      because NEC-2 must: a wire bonded to the ground plane shorts the
      source.  NEC-4 has no such limit, and `ground_contact.py` shows
      the standoff is not free -- 5 cm above against 5 cm below moves
      the feedpoint about 15 percent near half- and full-wave
      multiples, and up to x5.02 at a quarter wave, which is where the
      picker operates.

      It also retires the argument that made the standoff look safe:
      "0.01 m gives nearly the same answer" is true in PyNEC (x0.92)
      and false in NEC-4.2 (x1.31).

      Recipe, all three needed: split the drop at z = 0, since no
      segment may span the interface; `GE 0`, because `GE 1` rejects
      anything at or below it; and avoid z = 0 exactly, which puts the
      wire *in* the interface and returns a value inconsistent with
      both sides.  Buried is well behaved from 1 cm to 50 cm down.

      What it does not do is let the return sit *on* the ground.  That
      case is not expressible: the thin-wire kernel wants one medium
      around the conductor and a wire on the surface has half its field
      in each, so z = 0 returns a value consistent with neither side and
      the above branch fails below about 1 cm.  Closing the bracket from
      5 cm to 1 cm either side does not converge -- at a quarter wave it
      widens, x2.19 median against x1.57.  Insulation does not change
      this; soil at HF is a lossy dielectric, so contact is not shorting
      and coax and bare wire are the same case.

      So the decision is not a depth but a regime, and the honest
      justification for staying above ground is mechanical: real ground
      is not flat, and a centimetre or two of average clearance
      describes coax draped over grass and ruts.  Two things follow,
      both open:

      - is 5 cm the right clearance for that story, or 1-2 cm?  NEC-4
        puts 31 percent between them, and 5 cm was never chosen for a
        physical reason.
      - radials or a counterpoise under the turf are a genuinely
        different install, and burial models them well -- nearly flat
        from 1 to 50 cm down, so it needs no depth from the user.  That
        is where a second model would earn its keep, rather than
        between solvers.

- [ ] Decide the default return length.  25 ft is what a typical user's
      coax run is, and it gives the best agreement with the published
      tables of any value tried, but the ARRL specifies a quarter wave
      at the lowest band, about 66 ft on 80 m, and most published
      lengths do score better with a longer return.  Consider saying so
      in the page rather than moving the default: a long counterpoise
      flattens the score curve, so length choice matters less, which is
      more useful than any single length.
- [ ] Exercise the page in a browser for the things a machine cannot
      judge.  The mechanical half is automated in
      `docs/tools/browser/random-wire.spec.mjs` and runs in CI;
      `RANDOM_WIRE_BROWSER_CHECKS.md` is now only the judgement calls --
      whether the caveat text reads well, whether the recommendations
      look right for a real installation, whether anything has drifted
      that no assertion covers.

Tooling: `nec/random_wire/`, Python + PyNEC, `uv`-managed.

## Considered and declined

- Refitting the coefficients against NEC-4.2.  Measured rather than
  argued: fitted to each grid, the same form gives x1.25 median and
  x1.32 against x1.33 at the 90th for `h/lambda >= 0.05`.
  Indistinguishable where the page claims accuracy, so the refit would
  change the constants and not the answers.  Revisit if the model ever
  reaches below `h/lambda` 0.05, where the same form fits NEC-4.2 about
  twice as well, x1.71 worst against x3.12 -- that is the
  counterpoise-height direction, and it is what would make NEC-4.2 the
  right target.  See RANDOM_WIRE_MODEL.md.

- Deriving `marginPct` from a user-set `|Z|max` instead of a magic
  percentage, in the classical mode.  Buildable and honest, and declined
  because over most of its range the honest answer is that no length
  qualifies.  Measured: 8 percent buys about 2800 ohms and leaves 23
  percent of the axis, which makes the shipped default a defensible
  thing to have reached by feel.  Below that it saturates fast -- 1500
  ohms costs an 18 percent margin and leaves 0.6 percent of the axis,
  and 1000 ohms is unreachable at any margin.  A control whose range is
  mostly "nothing qualifies" teaches the user less than the fixed
  percentage it would replace.

- Modelling the ARRL counterpoise configuration -- source at the tuner,
  counterpoise folded around a room a metre or two up -- as a spike.
  Cheap to build, about eighty lines beside `end_fed_zin` reusing the
  existing sweep and fit machinery, but limited in what it could settle.
  NEC-2 has no walls, no mains wiring and no plumbing, so "indoors"
  becomes "folded wire in free space over ground", and the room size is
  a parameter nothing determines.  More to the point, at one to three
  metres the two-line form is already measured at x1.60, so a successful
  spike would establish what that configuration does while confirming
  the page still cannot score it.

## Open questions

- Counterpoise is now an explicit axis rather than a calibration
  constant (finding 4 forced this), but the two real cases differ:
  a thrown-out wire is well defined, while the coax shield carries
  common-mode current that makes "the feedpoint impedance" not a single
  well-defined number at all.  How much of that caveat reaches the user?
- How should the soil control be labelled so it does not imply that
  "good" ground gives a better match?  Finding 6 says it does not.
- Does the fitted `alpha`/`beta` surface interpolate cleanly over
  `h/lambda` once the return resonance is pulled out into its own term,
  or does it still need a spline?
