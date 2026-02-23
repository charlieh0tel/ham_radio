---
name: test-page
description: Run the automated Puppeteer test suite against antenna-matching.html.
disable-model-invocation: true
allowed-tools: Bash, Read
---

# Headless Page Test

Run the automated test suite for `antenna-matching.html`. The test plan is
documented in `antenna-matching-tests.md` and implemented by the Puppeteer
script `test-antenna-matching.mjs` in this skill directory.

## Steps

1. Start a local HTTP server on port 8787:
   ```
   python3 -m http.server 8787 &
   ```

2. Install puppeteer (if not already installed) and run the test script:
   ```
   PTEST=/tmp/ptest
   npm ls --prefix $PTEST puppeteer 2>/dev/null || npm install --prefix $PTEST puppeteer 2>&1 | tail -3
   NODE_PATH=$PTEST/node_modules node .claude/skills/test-page/test-antenna-matching.mjs 8787
   ```

3. Kill the HTTP server:
   ```
   kill %1 2>/dev/null; wait 2>/dev/null
   ```

4. Report results:
   - If exit code is 0: all tests passed.
   - If exit code is 1: report the failure summary printed by the script.
   - If exit code is 2: the test runner itself crashed — report the error.
