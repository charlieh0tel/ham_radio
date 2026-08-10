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

- [ ] Decide what the classical mode's default velocity factor should be.
      It ships 0.95, which is what the published tables assume, but the
      fitted model runs the antenna line at 1.00 and NEC backs it: 71 ft
      is 8.7 percent clear of the 40 m half wave at 0.95 and only 3.2
      percent clear at 1.00, and NEC rates it accordingly.  The two modes
      now disagree about a staple length.  Changing the default moves
      every classical recommendation and breaks agreement with tables the
      user can look up, so this is a judgement call, not a bug fix.
- [ ] Derive `marginPct` from a user-set `|Z|max` instead of a magic
      percentage.  Applies to the classical mode only.  Measured now, and
      the finding cuts both ways: 8 percent buys about 2800 ohms and
      leaves 23 percent of the axis, which is a defensible default to
      have reached by feel, but the control cannot express much below
      1800 ohms.  1500 ohms costs an 18 percent margin and leaves 0.6
      percent of the axis; 1000 ohms is unreachable at any margin.  So
      the feature is buildable and would be honest, and over much of its
      range the honest answer is that nothing qualifies.
- [x] Validate the keep-out widths: confirm `marginPct` values match the
      impedance excursions assumed.  Done, see the margin section of
      `RANDOM_WIRE_MODEL.md`.  The default holds up; current behaviour
      does not need to change.
- [ ] Expose conductor diameter, fixed at #14 AWG.  No longer blocked on
      evidence: gauge has been swept over #12 to #22 and the shipped #14
      table predicts every one of them within x1.44, against x1.39 for
      #14 itself, so the control can be offered honestly.  Remaining work
      is UI only.  The unun ratio is now selectable (1, 4, 9, 49, 64).

### Controls, decided

The model gains parameters the user can actually measure, and loses one
they cannot.  All four shipped in the page; the velocity factor survives
in the classical mode only, where it is part of that method's checkable
arithmetic rather than a model parameter.

- [x] **Height** becomes a user control.  It is the number people know.
- [x] **Return-path length** becomes a user control: the coax run for a
      shield-as-counterpoise install, or the wire length for a thrown-out
      counterpoise.  NEC finding 4 promoted this from a correction to a
      first-class parameter.  Default 25 ft.
- [x] **Soil type** becomes a user control, the three standard soils.
      Finding 6 is the caveat that rides with it: "better" ground does
      not mean a better match, it means a sharper resonance, so the
      labelling must not imply an ordering the physics does not have.
- [x] **Velocity factor stops being a control.**  It is installation
      dependent, users do not know it, and it is not an independent
      physical quantity: it is the emergent consequence of diameter,
      height, return path, insulation and sag.  It survives as a derived
      value the fit produces, optionally displayed.  Keep reading `?vf=`
      as an override so existing links resolve, per the `len`/`len_m`
      precedent.

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

- [x] Decide-first experiment.  Done, and the disagreement is material.
      Findings below.
- [x] Fit the model properly.  Done, `nec/random_wire/fit.py`: two lines
      in series, the antenna and the return, each with its own `alpha`,
      `beta` and `Z0` scale.  Both ends land at once, so the anchor
      problem is gone -- no single anchor forces the other end to
      `Z0^2 / (2 R)` any more.  `beta` is fitted rather than assumed,
      and the return has its own resonance rather than a correction
      folded into `alpha`.
      Coefficients ship, not code, because the page has no business
      solving a NEC model in the browser.  The modeller itself lives in
      the repo; see the licence note in `nec/random_wire/README.md` for
      why that is not a GPL problem.
- [x] Bound the error across the parameter space.  Done: |Z| within
      x1.35 worst case for `h/lambda >= 0.05`, degrading to x2.3 below
      that, which is 160 m and 80 m with a low wire.  See the error
      bound section of `RANDOM_WIRE_MODEL.md` for the per-band heights
      and for two hypotheses that failed to improve the low region.

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

- [ ] **Decide which NEC-2 the model belongs to.**  Running the fixture
      against nec2c 0.1.1 failed 26 of 30 cases, worst 65.7 percent, and
      the cause is not the deck.  In free space the two agree to five
      figures; over ground they differ by up to a third, converged.  The
      whole disagreement is the Sommerfeld-Norton implementation, and
      every shipped coefficient is fitted to nec2++'s.  Two ways out:
      refit offline against nec2c so both ends share a solver, which
      costs the sweeps again but makes the browser check consistent by
      construction; or keep the fit and have the button report the
      spread as a known implementation difference.  The first is
      cleaner, the second is cheaper and arguably more honest, since
      neither implementation is a reference for the other.
- [x] Say something when a published length scores badly.  Done: the
      impedance mode now carries a "Published lengths, scored" panel
      running the standard table through the model at the user's own
      site, with the velocity-factor difference named as the reason for
      the disagreements.  At the defaults 8 of the 10 pass, which is what
      makes the two that do not worth reading.
- [ ] Decide the default return length.  25 ft is what a typical user's
      coax run is, and it gives the best agreement with the published
      tables of any value tried, but the ARRL specifies a quarter wave
      at the lowest band, about 66 ft on 80 m, and most published
      lengths do score better with a longer return.  Consider saying so
      in the page rather than moving the default: a long counterpoise
      flattens the score curve, so length choice matters less, which is
      more useful than any single length.
- [ ] Have coefficients.py patch random-wire.html between marker
      comments instead of printing a block to paste.  The constants were
      hand-copied once and needed a separate script to verify; the
      generator should write them.  Do it when the constants are next
      regenerated.
- [x] Tabulate against return height and offer it as a control.  Done
      and answered no.  The full sweep shows the two-line *form* failing
      before the table does: given each group its own best coefficients
      the error still reaches x1.60 median at a 2 m return, and a 2D
      table measured x4.30 worst above 15 cm against x1.44 below it.
      The return stays assumed to lie on the ground.
- [x] Add a coupling term between the two lines.  Tried and not kept: a
      mutual term scaling `sqrt(Za Zr)` with an exponential decay in
      separation buys 9 percent at a 2 m return and nothing elsewhere,
      with its two parameters either railed or zero.  A scalar mutual
      term is too weak; an elevated return is a second radiator with its
      own current distribution and wants a coupled two-port, which is a
      different model rather than a term on this one.  Not worth doing
      unless elevated counterpoises become the point of the page.
- [ ] Exercise the page in a browser beyond the ribbon: the impedance
      mode's height, return-length and soil controls have never been
      driven, and a passing type check is not a rendering test.

- [x] Confirm the odd-`lambda/4` case is as bad as theory says before
      building UI around it.  It is not: finding 2 measures 133-3500
      ohms there, and the low-Z case the keep-out was meant to catch
      mostly does not occur once a real return path exists.  Do not
      build UI around it.

Tooling: `nec/random_wire/`, Python + PyNEC, `uv`-managed.

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
