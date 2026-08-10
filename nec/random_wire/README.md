# NEC modelling for the random wire picker

Offline instrument behind the impedance model in `docs/random-wire.html`.
It does not run at the site: it produces fitted coefficients that are
copied into the page, along with the error bound that becomes the page's
caveat text.  The approach and the measured findings are in
`docs/RANDOM_WIRE_MODEL.md`.

The point of keeping it in the repo is auditability.  The page's claim
to be defensible rests on constants with stated assumptions and a
bounded error, and constants whose producing code has been discarded
cannot be checked.  This is the source for them.

## Licence

These scripts are MIT, like the rest of the repo.  They import PyNEC,
which is GPL-3.0-only, but PyNEC is a declared dependency fetched from
PyPI, not vendored here.  MIT is GPL-compatible, so combining the two on
your own machine is fine; what would not be fine is copying PyNEC or
nec2c source into this repo, which is why nothing does.

The numeric output is a separate matter again: a program's output is not
covered by the program's licence, so the fitted constants carry no GPL
obligation into the MIT page.

## Running

```sh
uv run validate.py       # textbook cases; run this first
uv run sweep.py          # the full grid, ~9 minutes on 16 cores
uv run analyze.py        # tests the series decomposition against sweep.npz
```

`validate.py` is the regression test.  A quarter-wave monopole over
perfect ground should read near 36+j21 and a free-space half-wave dipole
near 73+j42, both overshooting slightly for a thin wire.  If those move,
distrust everything else.

`sweep.npz` is generated, not committed; `sweep.py` rebuilds it.

## Files

- `nec_model.py` -- the geometry: antenna wire at height h, vertical
  drop at the feedpoint, horizontal return run standing for the coax
  shield or a counterpoise.  Everything else imports this.
- `validate.py` -- textbook cases and an end-fed smoke test.
- `sweep.py` -- the full parameter grid, written to `sweep.npz`.
- `analyze.py` -- tests whether the return path is additive.
- `probe.py` -- compares NEC against the page's shipped model at both
  anchors, over height, return length and soil.
- `return_sweep.py` -- return length alone, showing its resonance.
- `chase.py` -- decomposes the quarter-wave disagreement.
- `ground_low.py` -- soil behaviour at low height, as curves.
