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

## Type Checking

`docs/tools/` holds a dev-time type checker. It is not part of the site:
nothing there is served, and the pages still run Babel standalone in the
browser exactly as before. eslint lints both pages; `tsc` checks
`sherwood.html` only. Getting `antenna-matching.html` past `tsc` needs
tighter ambient declarations for `mathjs` and `fmin` than `globals.d.ts`
has, so it stays out of `tsconfig.check.json`.

```sh
npm --prefix docs/tools install   # once
npm --prefix docs/tools run check   # tsc and eslint
npm --prefix docs/tools run lint    # eslint alone
```

`check` runs eslint after `tsc`, over the same extracted `.jsx`.  The rule
it exists for is `react-hooks/exhaustive-deps`: a dependency array that
lists a derived object rather than the inputs behind it is a class of bug
nothing but a linter finds.  It applies to `antenna-matching.html`, the
page with hooks; `sherwood.html` gets the recommended rules only.

Neither page has any test.  The only automated coverage is this check.

`tools/extract.mjs` pulls the `<script type="text/babel">` body into a
gitignored `.check/` directory, padded so a diagnostic's line number
matches the HTML. `tsc` then checks it with `checkJs` and `strict`.

The check must pass before committing and before pushing. A `pre-push`
hook is in `githooks/`; enable it with
`git config core.hooksPath githooks`. CI runs the same commands on any
push or PR touching `docs/`.

## Before Committing

Before proposing a commit, always:

0. **Type check**: `npm --prefix docs/tools run check` must pass clean.
1. **Syntax check**: Verify the HTML is well-formed and all `<script>` blocks have valid JavaScript/JSX syntax.
2. **Style review**: Ensure code follows the style guidelines above. No unused variables, no console.log left behind, no commented-out dead code.
3. **Lint**: `npm --prefix docs/tools run lint`. It covers both pages,
   and must be clean: no warnings, not just no errors.
4. **Math verification**: Pay special attention to:
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

Verify:
- The page loads without console errors (check browser DevTools)
- Smith chart renders correctly with proper aspect ratio
- Sliders respond and update the chart in real time
- Presets load and auto-tune produces reasonable matching networks
- Both Gamma match and Hairpin match modes work

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
