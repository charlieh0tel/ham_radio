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
EXPERIMENTAL ribbon and a list of caveats -- an unswept return height
that outweighs everything the model does fit, unconverged segmentation,
and a disagreement with the published tables over staple lengths -- that
a default should not be quietly wearing.  The impedance mode scores every
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

Still open:

- [ ] Derive `marginPct` from a user-set `|Z|max` instead of a magic
      percentage.  Applies to the classical mode only.  Measured now, and
      the finding cuts both ways: 8 percent buys about 2800 ohms and
      leaves 23 percent of the axis, which is a defensible default to
      have reached by feel, but the control cannot express much below
      1800 ohms.  1500 ohms costs an 18 percent margin and leaves 0.6
      percent of the axis; 1000 ohms is unreachable at any margin.  So
      the feature is buildable and would be honest, and over much of its
      range the honest answer is that nothing qualifies.

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

- [ ] **Consider refitting the coefficients against NEC-4.2.**  The
      model is fitted to nec2++, which passes the conductivity limit;
      NEC-4.2 passes it better at every height below 0.05 wl, and its
      ground treatment was reworked for exactly the regime this model
      lives in.  So the coefficients could be better than they are.

      Three costs to weigh first, none fatal but none free:

      - **Auditability.**  NEC-4 is licensed from LLNL and cannot be
        redistributed, so nobody without a licence could regenerate the
        constants.  `nec/random_wire/README.md` says plainly that the
        point of keeping the modeller in the repo is that constants
        whose producing code has been discarded cannot be checked.
        Fitting against a solver most readers cannot run weakens that,
        though it does not void it: the decks are generated and the
        comparison against nec2++ stays reproducible.
      - **Speed.**  `sweep.py` runs PyNEC in process, about 9 minutes on
        16 cores.  NEC-4 is a binary driven by decks, one process per
        solve, and it writes its Sommerfeld grid to `SOMD.NEC` in the
        working directory, so each solve needs its own.  Expect a large
        multiple of the current time.
      - **How much it would move.**  Unmeasured, and cheap to find out:
        solve the existing sweep points with both and compare, rather
        than refitting first.  Where the page actually operates -- the
        return at 0.0012 wl but the source 0.22 wl up -- nec2++ already
        reaches the limit, so the gain may be small.  If it is, the
        honest answer is to keep the current fit and cite NEC-4.2 as
        corroboration instead.

      Do the third of those before either of the others.
- [ ] Decide the default return length.  25 ft is what a typical user's
      coax run is, and it gives the best agreement with the published
      tables of any value tried, but the ARRL specifies a quarter wave
      at the lowest band, about 66 ft on 80 m, and most published
      lengths do score better with a longer return.  Consider saying so
      in the page rather than moving the default: a long counterpoise
      flattens the score curve, so length choice matters less, which is
      more useful than any single length.
- [ ] Exercise the page in a browser beyond the ribbon.  Checklist
      written: `RANDOM_WIRE_BROWSER_CHECKS.md`, covering the controls
      that changed, the verdicts, keyboard access, contrast, URL round
      trips, and the handful of things only a browser can catch.  Each
      item says what correct looks like, so it can be run without
      reading the code.

Tooling: `nec/random_wire/`, Python + PyNEC, `uv`-managed.

## Considered and declined

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
