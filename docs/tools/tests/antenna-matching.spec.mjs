// antenna-matching.html: the app renders, the modes switch, and state
// survives a round trip through the URL.
//
// The URL round trip is the case worth guarding.  Every mode serializes its
// own subset of the state, so a key added to one mode and not to its
// serializeUrl is silently dropped from a shared link -- which looks like
// nothing at all until someone opens the link.

import { test, expect } from '@playwright/test';

const PAGE = '/antenna-matching.html';

/**
 * Fail the test on any console error.  Babel transpiles in the browser here,
 * so a syntax error in the page shows up only at runtime.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {string[]} Collected error text; assert it is empty at the end.
 */
function collectConsoleErrors(page) {
  /** @type {string[]} */
  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', (err) => errors.push(String(err)));
  return errors;
}

test('renders the Smith chart without console errors', async ({ page }) => {
  const errors = collectConsoleErrors(page);
  await page.goto(PAGE);

  await expect(page.locator('h1.title')).toHaveText('Gamma Match');
  // The chart is SVG, drawn from the impedance math; if the math threw, the
  // heading would still render but the circles would not.
  await expect(page.locator('svg circle').first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('switches modes and keeps the chart', async ({ page }) => {
  const errors = collectConsoleErrors(page);
  await page.goto(PAGE);

  for (const [label, title] of [
    ['Beta (Hairpin) Match', 'Beta (Hairpin) Match'],
    ['OCFD', 'Off-Center Fed Doublet'],
    ['Gamma Match', 'Gamma Match'],
  ]) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.locator('h1.title')).toHaveText(title);
    await expect(page.locator('svg circle').first()).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test('puts the antenna impedance in the URL and reads it back', async ({ page }) => {
  await page.goto(PAGE);

  const resistance = page.getByLabel('Antenna resistance');
  await resistance.fill('30');
  await resistance.dispatchEvent('change');

  await expect(page).toHaveURL(/[?&]r=30\b/);

  // Reopen the link cold: the value must come back, not fall to the default.
  const url = page.url();
  await page.goto(url);
  await expect(page.getByLabel('Antenna resistance')).toHaveValue('30');
});

test('each mode round-trips its own parameters', async ({ page }) => {
  await page.goto(PAGE);

  await page.getByRole('button', { name: 'Beta (Hairpin) Match', exact: true }).click();
  const hairpin = page.getByLabel('Hairpin reactance');
  await hairpin.fill('80');
  await hairpin.dispatchEvent('change');
  await expect(page).toHaveURL(/[?&]hp=80\b/);
  await expect(page).toHaveURL(/[?&]mode=hairpin\b/);

  await page.goto(page.url());
  await expect(page.locator('h1.title')).toHaveText('Beta (Hairpin) Match');
  await expect(page.getByLabel('Hairpin reactance')).toHaveValue('80');
});

test('an unknown mode in the URL falls back rather than breaking', async ({ page }) => {
  const errors = collectConsoleErrors(page);
  await page.goto(`${PAGE}?mode=nonsense&gnd=nonsense`);

  await expect(page.locator('h1.title')).toHaveText('Gamma Match');
  expect(errors).toEqual([]);
});

test('a preset applies its impedance', async ({ page }) => {
  await page.goto(PAGE);

  await page.getByRole('button', { name: /^Yagi/ }).click();
  await expect(page.getByLabel('Antenna resistance')).toHaveValue('25');
});

test('auto-tune lowers SWR', async ({ page }) => {
  // Load from a URL, not bare: a bare load auto-tunes itself on mount, which
  // would leave nothing for this test to improve on.  These values are a
  // deliberately bad gamma match.
  await page.goto(`${PAGE}?mode=gamma&r=25&x=0&tap=1&rod=300&cap=30`);

  const swr = page.locator('.result-swr').first();
  await expect(swr).toBeVisible();
  const before = parseFloat((await swr.innerText()).match(/([\d.]+)\s*:\s*1/)[1]);

  await page.getByRole('button', { name: /auto.?tune/i }).first().click();
  await expect
    .poll(async () => parseFloat((await swr.innerText()).match(/([\d.]+)\s*:\s*1/)[1]))
    .toBeLessThan(before);
});
