# Agent Instructions for docs/

Root `AGENTS.md` applies here too; this file adds only what is specific
to this app.

## Project Overview

This is a GitHub Pages site (`docs/`) with `index.html` linking to one
self-contained tool per page:

- `antenna-matching.html`: antenna impedance matching with a Smith chart.
  React + inline JSX transpiled by Babel standalone, mathjs for complex
  arithmetic, fmin for optimization.
- `random-wire.html`: end-fed random wire lengths that avoid half-wave
  resonances on selected bands. React + Babel standalone, no other
  dependencies. Band plans (US, IARU regions 1-3) are a data table.
- `sherwood.html`: Sherwood receiver performance table. Plain JS with
  Chart.js.

## Code Style

- Write clean, readable JavaScript. Use modern ES6+ patterns and style;
  `const`/`let`, never `var`.
- Consistent 2-space indentation.
- Use template literals over string concatenation.

## Before Committing

Before proposing a commit, always:

1. **Syntax check**: Verify the HTML is well-formed and all `<script>` blocks have valid JavaScript/JSX syntax.
2. **Style review**: Ensure code follows the style guidelines above. No unused variables, no console.log left behind, no commented-out dead code.
3. **Lint**: Since there is no formal linter configured, manually review for common issues: missing semicolons (if the file uses them consistently), unclosed brackets, mismatched JSX tags, undeclared variables.
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
- **URL parameters**: The app may encode state in URL params. Ensure changes preserve backward-compatible URL parsing.
- **Accessibility**: Maintain readable contrast ratios in the dark theme. Ensure interactive controls are keyboard-accessible.
- **Stay in this directory.**
