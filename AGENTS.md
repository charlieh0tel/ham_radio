# Agent Instructions

## General

- Be extremely concise; sacrifice grammar for concision.
- Always list unresolved questions at end.
- Use built-in tools for file operations: globs for file search, grep
  for content search, read for viewing files.
- Do not request grep/sed/fd/find/ls/cat or similar CLI tools when you
  already have these capabilities built-in.
- Prefer ASCII in all code and user-facing strings (logs, CLI output,
  error messages).  Ask before using Unicode.


## Documentation

- Keep documentation (.md files) up to date with code changes.
- When work completes a tracked item, mark it done in `TODO.md`, if it
  is being used, in the same commit.


## Revision Control

- Do not add Claude or other agent attribution to anything (commit
  messages, pull requests, issues).
- Do not commit without permission.
- Never use -a to commit; always enumerate the files.
- All tests must pass before committing.
- Suggest making a commit before moving onto something unrelated; a PR
  should generally be one functional change.


## Programming

- Read code before modifying it.  Understand existing patterns and
  context before proposing changes.
- Prefer consistency above most other concerns.
- Be DRY.
- Keep functions short and focused; extract helpers when logic is
  reused.
- Avoid magic constants.
- Use meaningful names, especially for RF and math quantities
  (`zLoad`, `gammaL`, `susceptance`; not `x`, `tmp`).
- Don't abbreviate by dropping letters from the middle of a word.
  Truncation (cutting from the end) is OK.
- Comment only unintuitive or hard to understand code; always comment
  data structures.
- Comment non-obvious RF and math formulas, and cite their sources.
- Verify math against known references.  Watch sign conventions and
  unit conversions (degrees/radians, MHz/Hz).
- Calculate in SI internally.  Convert at the edges: read input and
  format output in whatever unit the user wants, but keep one coherent
  system in between.  Name the unit in the type, not only in the
  identifier.
- No trailing whitespace.
- Do not add dependencies without discussion.
- Run a type check (if appropripate), a syntax check and a style check
  before committing.


## Python

- Use `uv` for all dependency and environment management.
- Run `ruff format` and `ruff check` after changes and before commits.
- Run tests with `pytest`.


## Rust

- Run `cargo fmt` after changes and before commits.
- Run `cargo clippy` after major changes and before commits.
- Use relative imports.
- CLI code can use anyhow!  library code must *not* use anyhow!


## TypeScript Rules

- Write clean, readable JavaScript. Use modern ES6+ patterns and style;
  `const`/`let`, never `var`.
- Consistent 2-space indentation.
- Use template literals over string concatenation.
- Type every function parameter and return with JSDoc; the checker below
  runs under `strict`, so an unannotated parameter is an error.
- Name the unit in the type, not only in the identifier: `Feet`,
  `KiloHertz`, `MegaHertz` are declared as aliases in `random-wire.html`.
- Use `npm` (the committed `package-lock.json`) for dependency management.
- Run `npm run lint` (Biome) after changes and before commits.
- Run tests with `npm test` (Vitest).
