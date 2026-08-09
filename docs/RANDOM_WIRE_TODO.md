# random-wire.html TODO

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
  to this.
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

Done: the page now carries both methods behind a Method toggle
(`?mode=`), classical by default.  The impedance mode scores every
length by the geometric mean of the modelled SWR at the radio and
offers the local minima.  A worst-case score was tried first and
discarded: the lowest band always sets it, so it collapses into "prefer
the longest wire".

Still open:

- [ ] Derive `marginPct` from a user-set `|Z|max` instead of a magic
      percentage.  Applies to the classical mode only.
- [ ] Expose the unun ratio and conductor diameter, currently fixed at
      9:1 and #14 AWG.

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

- [ ] Decide-first experiment: run the impedance-optimal search offline
      and diff its recommended lengths against the current table.  If
      they largely agree (expected), the runtime stays pure arithmetic.
      Material disagreement is the interesting result and should be
      chased before shipping either model.
- [ ] Fit `alpha`: sweep NEC over wire lengths, diameters, and heights;
      fit the analytic model; bake constants into the page.
- [ ] Bound the error across the parameter space.  That bound becomes
      the caveat on the plot, e.g. "within ~2x over 20-60 ft, 1-30 MHz,
      15-30 ft high".
- [ ] Validate the keep-out widths: confirm `marginPct` values match the
      impedance excursions assumed.  This one could change current
      behavior.
- [ ] Confirm the odd-`lambda/4` case is as bad as theory says before
      building UI around it.

Tooling: scratch script, Python + PyNEC, `uv`-managed, results committed
as a short findings note.

## Open questions

- Is the assumed feed a 9:1 unun into a tuner, or should the unun ratio
  be a parameter?
- Model the counterpoise / radial explicitly, or fold it into the
  calibration?
