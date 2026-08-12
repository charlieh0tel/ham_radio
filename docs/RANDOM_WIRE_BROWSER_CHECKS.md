# random-wire.html: what to check in a browser

The type checker, the linter and 71 tests all pass without a browser ever
opening the page.  None of them can see a control that does not render, a
button that activates the wrong thing, or text that has become unreadable.
Everything below changed recently and has never been driven by hand.

```sh
cd docs && python3 -m http.server 8000
# then http://localhost:8000/random-wire.html
```

Each item says what to do and what correct looks like, so a failure is
recognisable without knowing the code.

## Impedance mode, the installation panel

These controls are new or reworked and none has been used.

- [ ] **Tuner.** Four buttons: Rig ATU, Compact auto, Wide-range, Roller /
      link.  Opens on **Rig ATU**.  Clicking each changes the ok/poor
      verdicts and the hint's stated limit (3, 5, 9, 12 to 1).  Stricter
      tuners must mark *fewer* lengths ok, never different ones.
- [ ] **Wire height.** Slider, reads 30 ft by default.  Moving it changes
      the suggestions.
- [ ] **Return path.** Slider, reads 55 ft by default.  **Drag the height
      above the return** -- the return display should stop falling and hold
      at the height, because a return cannot be shorter than the drop it
      starts with.
- [ ] **Return presets.** "Drop + 25 ft coax" should set the return to
      height + 25 ft, so at 30 ft it reads 55 ft.  "λ/4 on 40 m" should set
      it to 35 ft exactly, not 35 ft plus the drop.  This one was wrong
      before: the preset delivered a quarter wave *plus* the height.
- [ ] **Ground.** Three buttons, Sandy / Medium / Damp.  **Click the word
      "Ground" itself** -- nothing should happen.  It used to activate
      "Sandy", because a `<label>` binds to its first button.
- [ ] **Unun ratio.** Same check on the word "Unun ratio": it should not
      activate 1:1.

## The verdicts

- [ ] **Published lengths, scored.** Four columns: Length, Average, Worst
      band, Verdict.  With the default Rig ATU, expect **none** to read ok.
      Switch to Roller / link and expect most to.  The point of the panel
      is that the page has an opinion about 71 ft rather than omitting it.
- [ ] **Best lengths.** The Worst column is coloured: green inside the
      tuner's limit, orange outside.  When nothing on offer is inside it, a
      note above the table should say so and point at the transformer ratio
      or the band in the last column.
- [ ] **Wire length verdict.** The headline box turns green or orange, and
      it must follow the **worst band**, not the average.  Find a length
      whose average is low and whose worst band is high; the box must be
      orange.

## The NEC deck panel

Impedance mode only, and new.  Nothing automated opens a file dialog or a
second tab.

- [ ] **Panel presence.** "NEC deck" appears in impedance mode with a
      length in hand, and is **absent in classical mode**, where the page
      never asked for a height, a return path or a soil.
- [ ] **Download .nec.** Saves `random-wire-<length>m.nec`.  Open it: the
      `CM` lines should name the length, height, return and soil showing
      on screen, and the `GN` card should carry the constants for the
      selected ground (5 / 0.001, 13 / 0.005, 20 / 0.03), not 13 / 0.005
      always.
- [ ] **The deck tracks the controls.** Change the length, the height and
      the soil, download again, and confirm all three moved in the file.
- [ ] **Download .antennasim.** Load it in AntennaSim from the **Wire
      Editor** page, Open (Ctrl+O).  Three wires, fed at the end of the
      long one, sweep 7-29.7 MHz, and the ground reading *custom* with
      this page's two constants -- that last is the whole reason the
      format is written.  Opening it from the Simulator page instead
      should say so plainly rather than doing nothing.
- [ ] **The deck solves.** `nec2c -i <file> -o out` should print one
      "ANTENNA INPUT PARAMETERS" block per swept frequency, 201 of them.
      A deck with no execution card loads, echoes the geometry and
      computes nothing, which is what it did before the `XQ` card.

## Display

- [ ] **Units.** Switch feet to metres and back.  A length you **typed**
      must survive; a length the page **chose** may re-round.  It used to
      discard both.
- [ ] **Length field.** Type into it slowly.  It should not reformat under
      the cursor mid-number, and a partial entry like `5.` should not blank
      the field.
- [ ] **Panel order.** Method, Band plan, Bands of interest, Display, then
      the installation or rule panel.
- [ ] **EXPERIMENTAL ribbon.** Impedance mode only.  **Scroll down** -- it
      should scroll away with the page, not stay pinned over the right-hand
      column.

## Classical mode

- [ ] **Clearance slider.** The hint should now say what the margin buys:
      how much of the axis stays usable and the worst band of the worst
      length offered, as SWR through the transformer.  Moving the slider
      changes both numbers.
- [ ] **Velocity factor.** Present in classical mode only.  It should be
      absent in impedance mode, which fits its own.

## Keyboard and contrast

- [ ] **Tab through the whole page.**  Every control should take focus with
      a visible ring, including the **lengths in the three suggestion
      tables**, which are now buttons.  They used to be unreachable.
- [ ] **Accept a recommendation with Enter or Space** on a focused length.
- [ ] **Read the caveats.** The grey explanatory text under each control
      was 3:1 contrast and is now 4.5:1.  It should be comfortable rather
      than faint.

## Things a browser is the only way to catch

- [ ] Console clean on load and after exercising every control.
- [ ] Narrow the window to phone width.  Nothing should overlap or scroll
      sideways; the ribbon is the likeliest offender.
- [ ] Copy the URL after changing several controls, open it in a new tab,
      and confirm the page comes back identical.
- [ ] Open a bare `random-wire.html?len=70` -- the pre-SI spelling, in feet
      -- and confirm it lands on the same wire as `?len_m=21.336`.
