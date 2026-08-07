# Agent Instrucitons

## Critical Rules

- Be extremely concise; sacrifice grammar for concision.
- Use built-in tools for file operations.
- Use globs for file search, grep for content search, read for viewing files.
- Do not request grep/sed/fd/find/ls/cat or similar CLI tools when you
  already have these capabilities built-in.
- Always list unresolved questions at end.
- Keep documention (.md files) up to date with code changes.
- When work completes a tracked item, update `TODO.md`, if it is being
  used, in the same commit by marking that item done.


## Revision Control

- Do not add Claude or other agent attribution to anythign (commit
  messages, pull requests, issues).
- Do not commit without permission.
- PRs should generally be comprised of one functional change; suggest
  making a commit before moving onto something unrelated.
- All tests must pass before committing.
- Never use -a to commit; always enumerate the files.


## Programming Rules

- Read code before modifying it.  Understand existing patterns and
  context before proposing changes.
- Prefer ASCII in all code and user-facing strings (logs, CLI output,
  error messages).  Ask before using Unicode.
- Prefer consistency above most other concerns.
- Do not add trivial, obvious or redundant comments.
- Be DRY.
- Avoid magic constants.
- Only comment unintiutive or hard to understand code.
- Always comment data structures.
- Don't abbreviate by dropping letters from the middle of a word.
  Truncation (cutting from the end) is OK.


## Python Rules

- Use `uv` for all dependency and environment management.
- Run `ruff check` after changes and before commits.
- Run `ruff format` after changes and before commits.
- Run tests with `pytest`.

## Rust Rules

- Always run `cargo fmt` after changes and before commits.
- Always run `cargo clippy` after major changes and always before commits.
- All tests must pass before committing (`cargo test`).
- Use relative imports.
- CLI code can use anyhow!  library code must *not* use anyhow!
