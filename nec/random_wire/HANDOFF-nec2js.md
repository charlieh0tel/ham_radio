# Handoff: the Sommerfeld near-ground investigation

Work done in `~/src/ham_radio` that has consequences here. Nothing in
this repo has been modified.

## The headline, which reverses an earlier conclusion

`investigations/sommerfeld_near_ground.nec` records nec2++ reaching the
conductivity limit and nec2c missing it by 92 percent. That was read as
a bug in nec2c, and a reproducer was written to file upstream.

**It is not a bug in nec2c.** The nec2c maintainer has a `validation`
branch (`KJ7LNW/nec2c`, `d1fcfe8`) carrying two genuine `somnec.c`
transcription slips, and it also builds `nec2dx`, the original NEC-2
FORTRAN. Running both:

- the fixes move nec2c *onto* nec2dx to five figures
- they leave the near-ground miss untouched
- `nec2dx` misses by the same amount

So NEC-2's own Sommerfeld evaluation fails the limit near the interface.
The deck's existing comment already suspected this via aegnec2, which
links the original SOMNEC. `nec2dx` confirms it.

**NEC-4.2 settles which side is right.** It shares no code with nec2++,
its ground treatment was reworked for this regime, and it lands on
nec2++'s side, closer to the limit at every height. That also kills the
strongest objection to the test, which is that sigma 1e10 might be
probing numerical conditioning rather than the method: if it were,
NEC-4.2 would struggle too.

Full measurements, feedpoint resistance under `GN 2` at sigma 1e10
against `GN 1`, correct value zero everywhere:

| height | NEC-4.2 | nec2++ | nec2c | nec2c-val | nec2dx | nec2dxs | aegnec2 |
|---|---|---|---|---|---|---|---|
| 0.5 wl | +0.00% | +0.00% | +0.00% | +0.00% | -0.00% | -0.00% | +0.00% |
| 0.2 wl | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | *crash* | +0.00% |
| 0.1 wl | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | *crash* | +0.00% |
| 0.05 wl | +0.00% | +0.00% | +0.00% | +0.00% | +0.00% | *crash* | +0.00% |
| 0.02 wl | +0.05% | +0.77% | +91.89% | +91.91% | +91.92% | *crash* | +91.92% |
| 0.01 wl | +0.46% | -0.69% | -95.35% | -95.08% | -95.09% | *crash* | -95.09% |
| 0.005 wl | +2.90% | +8.21% | +3037.98% | +3039.24% | +3039.26% | *crash* | +3038.92% |
| 0.002 wl | +50.53% | +125.70% | +46607.55% | +46612.07% | +46613.28% | *crash* | +46609.83% |

Impedance only; these runs used `XQ` with no `RP`, so they say nothing
about the average power gain half of the deck's claims.

Nobody is right at the bottom. The split is about where each stops
working, not about one being correct everywhere.

## Tasks

Decided so far: task 1 is wanted, task 4 is on hold, and **no report goes
upstream yet**. `sommerfeld_report.html` exists but is not to be sent.

### 1. Fix the dipole height in the deck

`investigations/sommerfeld_near_ground.nec` line 27 has a height that is
not quite 0.02 wl. At 145.9 MHz, lambda is 2.054780384 m, so 0.02 wl is
0.041095608 m. The file says `0.041091`, which is 0.019998 wl, off by
4.6 um.

    -GW 1 11 -0.500000 0.000000 0.041091 0.500000 0.000000 0.041091 0.001000
    +GW 1 11 -0.500000 0.000000 0.041096 0.500000 0.000000 0.041096 0.001000

Physically irrelevant at 0.011 percent, though it does reach the last
digit of the recorded results; see the check below. It matters mainly
because
`investigations/sommerfeld.mjs` computes the height the same way this
correction does, so the committed deck and the harness's generated deck
currently disagree, and anyone reproducing a row by hand will hit it.
Origin of `0.041091` unknown; likely hand-entered.

The `CM` comment says "41.1 mm", which stays true either way.

One thing to check after applying it. The recorded resistances are quoted
to five and six figures, and a 0.011 percent change in height can reach
the last of those. Measured at the corrected height, nec2c is +91.89
percent where the block records +91.88, which is consistent with the
height being the difference. So re-measure the four feedpoint numbers and
the three average power gains rather than assuming they carry over, and
if any move, the block is the place to record it.

### 2. Teach the harness about NEC-4

`STYLES` in `investigations/sommerfeld.mjs` has `flags`, `attached`,
`stdio`, `jobname`. NEC-4 needs a fifth, taking two positional
arguments:

    nec4d42 in.nec out.txt

Given no arguments it prompts for the same two names instead, so a
`stdio`-style invocation dies on EOF. `-i`/`-o` are not recognised: it
ignores them and prompts anyway. Both working forms give identical
results; positional is the one to implement.

**Gotcha worth encoding:** NEC-4 caches its Sommerfeld grid in
`SOMD.NEC` in the *working directory*, and reuses it. Two symptoms seen:
the second run of the same deck produced a 6.8 KB report where the first
produced 133 KB, because the grid dump was skipped; and the file was
silently created in whatever directory the harness happened to run from.
Run each solve in its own scratch directory. Re-running the whole sweep
with that isolation gave identical numbers, so no stale grid corrupted
the table above, but only because frequency and ground were constant
across it. A sweep that varied either would have been wrong.

### 3. Consider refreshing the deck's comment block

It currently reports nec2++, nec2c, aegnec2 and "NEC-2D segmentation
fault". Worth adding NEC-4.2 and nec2c's `validation` branch, and worth
rewording the conclusion: the deck presents this as NEC-2 failing, which
is right, but the surrounding project treated it as an nec2c defect,
which is wrong.

`nec2dxs` (`~/src/nec2/nec2dxs`) segfaults with a core dump at every
height below 0.5 wl, immediately after printing the ground constants, so
it dies in the Sommerfeld setup rather than returning a wrong number.
That matches the deck's "NEC-2D segmentation fault" note.

### 4. The opportunity: `necpp-wasm` -- ON HOLD

Not being pursued right now. Recorded because it is the reason the
question matters, not as a task.


`ham_radio`'s `docs/random-wire.html` wants an in-browser NEC check. It
is blocked, permanently, on `nec2c-wasm`: the page models a feedline
5 cm off the soil, which is 0.0012 wl on 40 m, and nec2c will be about
30 percent off there forever because that is what NEC-2 does. No
upstream fix will change it.

A **nec2++ wasm build is the only thing that unblocks it**, and
`packages/necpp-wasm` is well past a sketch: prebuilt `necpp.wasm` and
an inline variant, a runner, C++ bindings, and a test suite exercising
every binding. So the ham_radio fallbacks -- move the offline fit to
nec2c so both ends are wrong together, or ship the button reporting a
known spread -- may not be needed.

The measurement that would settle it has not been made: run
`sommerfeld.mjs` against the necpp-wasm runner and confirm it reproduces
the nec2++ column rather than the nec2c one. That is a small job and it
converts "should be equivalent" into a number. Left undone because this
item is on hold, not because it is hard.

## Does `investigations/` still earn its place?

Yes, and the overlap runs the other way: `sommerfeld_cross.py` in
ham_radio duplicates part of what is here, not the reverse.

- `average-power-gain.mjs` is not duplicated anywhere. It measures a
  different quantity through a different code path -- far-field
  integration rather than the current solution -- against a closed-form
  answer that needs no second solver. That last property makes it the
  harder check to argue with: it cannot be dismissed as one
  implementation disagreeing with another. Nothing on the ham_radio side
  does this.
- `sommerfeld.mjs` is the only thing that runs the **wasm** build, and
  the only thing that exercises this repo's own `buildDeck` and
  `parseOutput`. `sommerfeld_cross.py` hand-writes cards and bypasses
  both, so it tests engines while this tests the package.
- `sommerfeld_near_ground.nec` is the pinned deck and the record of
  results. The Python side generates decks and discards them.

They belong here because the question is this repo's: can the solver
this package ships be trusted near ground, and should it carry nec2++
instead. That decision is made here.

What has changed is their role. They were investigations into an open
question, and the question is now answered, so they are acceptance
criteria: the definition of what a correct solver must do in this
regime. If `necpp-wasm` lands, `sommerfeld.mjs` is the test that proves
it -- passing where `nec2c-wasm` fails. Worth reframing the file headers
to say that, and perhaps the directory name with them.

## Where the instruments are

`~/src/ham_radio/nec/random_wire/`:

- `sommerfeld_cross.py` -- the table above. Takes solvers as
  `name=style:path`, styles `flags` / `attached` / `stdio` / `jobname`,
  matching this repo's names, plus `positional` and `prompt` for NEC-4.
  `--decks=DIR` writes the 16 decks out. Runs each solve in its own
  directory for the `SOMD.NEC` reason above.
- `nec2c_ground_bug.py` -- the same limit for the random-wire
  installation, swept in conductivity rather than height.
- `sommerfeld_report.html` -- the write-up prepared for the NEC
  maintainers, self-contained.

## Binaries used

| what | where | style |
|---|---|---|
| NEC-4.2 | `/usr/bin/nec4d42` | two positional args |
| nec2++ | `~/src/necpp/_install_/bin/nec2++` | `attached`, needs `LD_LIBRARY_PATH=~/src/necpp/_install_/lib` |
| nec2dxs | `~/src/nec2/nec2dxs` | `stdio` |
| aegnec2 | `~/src/aegnec2/_install_/bin/aegnec2` | `jobname` |
| nec2c, nec2c-val, nec2dx | built into a scratch dir, **now gone** | `flags` |

Rebuilding the nec2c three:

    git clone https://github.com/KJ7LNW/nec2c && cd nec2c
    git checkout validation && ./autogen.sh && ./configure && make
    # ./nec2c and, on this branch only, the FORTRAN ./nec2dx
    # master is 55be1e0 for the stock column

NEC-4 is licensed from LLNL and cannot be redistributed, so that column
is not reproducible from source by a third party.

## Repo state when this was written

On `test-coverage`, 4 commits ahead of `origin/main`, clean. The most
recent three are necpp-wasm work -- bindings exercised and fixed,
results reported in nec2++'s own units -- and this file is tracked among
them. Nothing else here was touched from the ham_radio side.

Reported by the author: **nec2pp-wasm is now in good shape.** That is
the piece task 4 turns on.

## One loose end

The commit messages for both `validation` fixes state the slips reach
necpp: "The slip lives only in the NEC lineage (nec2c to necpp and
xnec2c); nec2dx.f to nec2dxs is unaffected." At `tmolteno/necpp`
`a8e829e` neither site reads that way -- the gate is
`fabs(real(a1))+fabs(imag(a1))` and `evlua` is a plain `if/else`. The
history between the two codebases has not been traced, so this is an
observation and not a correction; whoever knows that lineage will place
it faster.
