# Agent Instructions for docs/

Root `AGENTS.md` applies here too; this file adds only what is specific
to this app.

## Project Overview

This is a GitHub Pages site (`docs/`) with `index.html` linking to one
self-contained tool per page:

- `antenna-matching.html`: antenna impedance matching with a Smith chart.
  React + inline JSX transpiled by Babel standalone, mathjs for complex
  arithmetic, fmin for optimization.
- `sherwood.html`: Sherwood receiver performance table. Plain JS with
  Chart.js.

`random-wire.html` is a stub that redirects: the random wire calculator
and the NEC work behind it moved to
https://github.com/charlieh0tel/endfed .  Keep the stub, since links to
the old URL are out in the world; it carries the query string over.

## Code Style

- Name the unit in the type, not only in the identifier.
- Do not annotate a lookup table with `Object<string, ...>`. That widens
  its keys to `string` and defeats the narrowing that keeps a bad URL
  parameter out of the table.

## Checks and Tests

`docs/tools/` holds the dev-time checks. It is not part of the site:
nothing there is served, and the pages still run Babel standalone in the
browser exactly as before. `tsc` and eslint both cover both pages.

```sh
npm --prefix docs/tools install   # once
npx --prefix docs/tools playwright install chromium   # once
npm --prefix docs/tools run check   # tsc and eslint
npm --prefix docs/tools run lint    # eslint alone
npm --prefix docs/tools test        # Playwright, both pages
```

`check` runs eslint after `tsc`, over the same extracted `.jsx`.  The rule
it exists for is `react-hooks/exhaustive-deps`: a dependency array that
lists a derived object rather than the inputs behind it is a class of bug
nothing but a linter finds.  It applies to `antenna-matching.html`, the
page with hooks; `sherwood.html` gets the recommended rules only.

The pages carry JSDoc types, checked under `strict` with `checkJs`.  Two
things there are worth knowing.  `@type {Object}` on an object literal is
worse than no annotation at all: it erases the shape `tsc` would infer,
and 225 of the 318 errors in the first pass over `antenna-matching.html`
traced back to it.  And `MODE_MAP` is indexed at runtime, so the app
cannot prove it holds a mode's own result type; that is asserted once,
with a cast, at `const modeDef = ...`.

`npm test` drives both pages in a real Chromium via Playwright, served
over HTTP from `docs/`.  The CDN dependencies are not stubbed -- that is
how the pages actually run -- but `sherwood.html`'s data fetch is, since
those tests are about the table parser, not about sherweng.com being up.
The case most worth keeping covered is the URL round trip: each mode
serializes its own subset of the state, so a key added to one mode and
not to its `serializeUrl` silently drops out of a shared link.

`tools/extract.mjs` pulls the `<script type="text/babel">` body into a
gitignored `.check/` directory, padded so a diagnostic's line number
matches the HTML. `tsc` then checks it with `checkJs` and `strict`.

The check and the tests must pass before committing and before pushing.
A `pre-push` hook is in `githooks/`; enable it with
`git config core.hooksPath githooks`. CI runs the same commands on any
push or PR touching `docs/`.

## Before Committing

Before proposing a commit, always:

1. **Type check**: `npm --prefix docs/tools run check` must pass clean.
2. **Test**: `npm --prefix docs/tools test` must pass clean.
3. **Syntax check**: Verify the HTML is well-formed and all `<script>` blocks have valid JavaScript/JSX syntax.
4. **Style review**: Ensure code follows the style guidelines above. No unused variables, no console.log left behind, no commented-out dead code.
5. **Lint**: `npm --prefix docs/tools run lint`. It covers both pages,
   and must be clean: no warnings, not just no errors.
6. **Math verification**: Pay special attention to:
   - Complex number operations (conjugates, magnitudes, phases)
   - Impedance / admittance conversions
   - Gamma (reflection coefficient) calculations
   - Smith chart coordinate mappings (normalized impedance to chart position)
   - Matching network formulas
   - Wavelength / frequency conversions and band edge data

## Testing Locally

Open the HTML file directly in a browser:

```sh
# From the docs/ directory:
xdg-open antenna-matching.html
# or
python3 -m http.server 8000
# then visit http://localhost:8000/antenna-matching.html
```

`npm test` covers the console-error, mode-switch, preset, auto-tune and
URL round-trip cases.  What it does not judge is whether the result looks
right, so by hand verify:
- Smith chart renders correctly with proper aspect ratio
- Sliders respond and update the chart in real time
- Auto-tune produces a physically reasonable matching network
- All three modes (Gamma, Hairpin, OCFD) draw their overlays

## Deployment

The `docs/` directory is served by GitHub Pages from the `master` branch. Pushing to `master` is a deployment — treat it accordingly.

## Additional Guidelines

- **Preserve working state**: Each tool is a single file. A bad edit breaks everything. Be conservative with refactors.
- **Test both matching modes**: Changes to shared code (Smith chart drawing, impedance math) must be verified in both Gamma and Hairpin match modes.
- **Respect the single-file architecture**: Do not split into multiple files unless the user requests it. The single-file design is intentional for GitHub Pages simplicity.
- **External dependencies are loaded from CDN** (React, ReactDOM, Babel, mathjs, fmin).
- **Browser compatibility**: The app uses modern JS features transpiled by Babel. Ensure nothing relies on bleeding-edge APIs without checking browser support.
- **URL parameters**: The app may encode state in URL params. Ensure changes preserve backward-compatible URL parsing. When a parameter's unit changes, give the new unit a new key and keep reading the old one.
- **Accessibility**: Maintain readable contrast ratios in the dark theme. Ensure interactive controls are keyboard-accessible.
- **Stay in this directory.**
