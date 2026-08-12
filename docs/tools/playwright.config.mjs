import { defineConfig, devices } from '@playwright/test';

/**
 * The type checker proves the page compiles and the node tests prove the
 * DOM-free half computes.  Neither can see a control that does not render,
 * a button that activates the wrong thing, or text that has become
 * unreadable.  These tests open the real page, served exactly as GitHub
 * Pages serves it, and drive it.
 *
 * Chromium only, deliberately: this checks our own behaviour, not browser
 * compatibility, and a second engine would double the run for no new
 * information about the page.
 */
export default defineConfig({
  testDir: './browser',
  testMatch: '**/*.spec.mjs',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: process.env.CI ? 'list' : [['list', { printSteps: false }]],
  use: {
    baseURL: `http://127.0.0.1:${process.env.PORT ?? 4173}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'node serve.mjs',
    url: `http://127.0.0.1:${process.env.PORT ?? 4173}/random-wire.html`,
    reuseExistingServer: !process.env.CI,
    stdout: 'ignore',
  },
});
