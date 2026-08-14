// Browser tests for the two pages in docs/.
//
// The pages are static and self-contained, but they are not file:// friendly:
// antenna-matching.html rewrites the URL with history.replaceState, and
// sherwood.html is only meaningful when its fetch can be intercepted.  So the
// suite serves docs/ over HTTP and drives the real page.
//
// The pages load React, Babel, mathjs and fmin from a CDN, which the tests do
// not stub: that is how the pages actually run, and a test against a mocked
// React would not be testing the shipped artifact.  sherwood.html's data fetch
// IS stubbed -- those tests are about the parser, not about sherweng.com being
// up.

import { defineConfig, devices } from '@playwright/test';

const PORT = 8123;

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: `python3 -m http.server ${PORT} --bind 127.0.0.1 --directory ..`,
    url: `http://127.0.0.1:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
  },
});
