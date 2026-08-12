# random-wire.html: what to check in a browser

Most of what used to be here is now automated, in
`docs/tools/browser/random-wire.spec.mjs`:

```sh
npm --prefix docs/tools run test:browser
```

That suite drives the real page, served as GitHub Pages serves it, and
covers the control wiring, the tuner verdicts, the presets, unit and URL
round trips, phone-width layout, contrast, console cleanliness and
keyboard access.  CI runs it on any push touching `docs/`.

What follows is only what a machine cannot judge.  To look by hand:

```sh
npm --prefix docs/tools run serve
# then http://127.0.0.1:4173/random-wire.html
```

## Judgement, not assertion

- [ ] **Does the caveat text read comfortably?**  The suite proves every
      piece of small print clears 4.5:1 against its background.  It
      cannot tell you whether the hint under a control explains the
      control, or whether there is too much of it.
- [ ] **Do the recommendations look sensible for a real installation?**
      Enter your own height, counterpoise and soil and see whether the
      lengths offered match what you would actually put up.  The model's
      error bound is in `RANDOM_WIRE_MODEL.md`; this is the sanity check
      that sits outside it.
- [ ] **Is the EXPERIMENTAL ribbon saying the right thing?**  The suite
      checks that it scrolls away rather than pinning.  Whether the page
      still deserves the ribbon is a judgement about the model.
- [ ] **Does anything look wrong that no assertion covers?**  Spacing
      that has drifted, a panel in an order that reads oddly, a control
      that is technically reachable but awkward to use.

## Known, not yet decided

- [ ] **The counterpoise slider has a dead zone.**  The return path is
      measured from the feedpoint, so it includes the vertical drop and
      cannot be shorter than the wire height.  At the default 30 ft
      height the bottom half of the slider therefore does nothing: it
      moves, and the readout stays at 30.0 ft.  The physics is right and
      the presentation is not.  See `RANDOM_WIRE_TODO.md`.
