# CLAUDE.md — Project Instructions

## Project Overview

This is a GitHub Pages site (`docs/`) containing an interactive antenna impedance matching tool with a Smith chart. The app is a single-file React application (`antenna-matching.html`) using inline JSX transpiled by Babel standalone, with mathjs for complex arithmetic and fmin for optimization.

## Code Style

- Write clean, readable JavaScript. Use `const`/`let` (never `var`).
- Use meaningful variable names, especially for RF/math quantities (e.g., `zLoad`, `gammaL`, `susceptance` — not `x`, `tmp`).
- Keep functions short and focused. Extract helpers when logic is reused.
- Prefer descriptive names over comments, but do comment non-obvious RF engineering formulas and their sources.
- Consistent 2-space indentation. No trailing whitespace.
- Use template literals over string concatenation.

## Before Committing

**Never commit without explicit user permission.** Never add a Co-Authored-By line or any other attribution to commits.

Before proposing a commit, always:

1. **Syntax check**: Verify the HTML is well-formed and all `<script>` blocks have valid JavaScript/JSX syntax.
2. **Style review**: Ensure code follows the style guidelines above. No unused variables, no console.log left behind, no commented-out dead code.
3. **Lint**: Since there is no formal linter configured, manually review for common issues: missing semicolons (if the file uses them consistently), unclosed brackets, mismatched JSX tags, undeclared variables.
4. **Math verification**: Double-check all RF math — impedance transformations, reflection coefficient calculations, Smith chart geometry, and matching network formulas. Verify against known references. Pay special attention to:
   - Complex number operations (conjugates, magnitudes, phases)
   - Impedance ↔ admittance conversions
   - Gamma (reflection coefficient) calculations
   - Smith chart coordinate mappings (normalized impedance ↔ chart position)
   - Sign conventions and unit conversions (degrees ↔ radians, MHz ↔ Hz)

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

- **Preserve working state**: This is a single-file app. A bad edit breaks everything. Be conservative with refactors.
- **Test both matching modes**: Changes to shared code (Smith chart drawing, impedance math) must be verified in both Gamma and Hairpin match modes.
- **Respect the single-file architecture**: Do not split into multiple files unless the user requests it. The single-file design is intentional for GitHub Pages simplicity.
- **External dependencies are loaded from CDN** (React, ReactDOM, Babel, mathjs, fmin). Do not add new CDN dependencies without discussion.
- **Browser compatibility**: The app uses modern JS features transpiled by Babel. Ensure nothing relies on bleeding-edge APIs without checking browser support.
- **URL parameters**: The app may encode state in URL params. Ensure changes preserve backward-compatible URL parsing.
- **Accessibility**: Maintain readable contrast ratios in the dark theme. Ensure interactive controls are keyboard-accessible.
