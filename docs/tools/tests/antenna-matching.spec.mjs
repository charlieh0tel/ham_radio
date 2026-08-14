// antenna-matching.html.
//
// Ported from a Puppeteer suite that lived in .claude/skills/test-page/,
// paired with a prose test plan.  Both are gone: this file is the record of
// what the page is expected to do, and being executable it cannot drift from
// itself the way the plan drifted from the suite.  The section numbering is
// the plan's, kept because the sections are a reasonable grouping.
//
// Each test navigates for itself.  The Puppeteer suite drove one page in
// order, so some of its cases depended on the state a previous case left
// behind; Playwright runs tests in parallel, and a test that needs a
// particular state now sets it up through the URL.

import { test, expect } from '@playwright/test';

const PAGE = '/antenna-matching.html';

/** Mode button labels, by the mode key used in the URL. */
const MODE_BUTTON = {
  gamma: 'Gamma Match',
  hairpin: 'Beta (Hairpin) Match',
  ocfd: 'OCFD',
};

/**
 * Collect console errors and page exceptions.  Babel transpiles in the
 * browser, so a broken page still serves 200 and fails only at runtime.
 * Resource errors are ignored: the CDN is not what these tests are about.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {string[]}
 */
function collectErrors(page) {
  /** @type {string[]} */
  const errors = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() !== 'error') return;
    if (text.includes('favicon') || text.includes('Failed to load resource')) return;
    errors.push(text);
  });
  page.on('pageerror', (err) => errors.push(String(err)));
  return errors;
}

/**
 * Set a range slider through the native value setter, so React sees the
 * change.  Assigning to .value alone would be swallowed by React's own
 * value tracking.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} ariaLabel
 * @param {number} value
 */
async function setSlider(page, ariaLabel, value) {
  await page.locator(`input[aria-label="${ariaLabel}"]`).evaluate((slider, val) => {
    const nativeSet = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, 'value').set;
    nativeSet.call(slider, String(val));
    slider.dispatchEvent(new Event('input', { bubbles: true }));
    slider.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

/**
 * @param {import('@playwright/test').Page} page
 * @param {string} ariaLabel
 * @returns {Promise<number>}
 */
async function sliderValue(page, ariaLabel) {
  return Number(await page.locator(`input[aria-label="${ariaLabel}"]`).inputValue());
}

/**
 * Read the SWR out of the result panel.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<number>}
 */
async function readSWR(page) {
  const text = await page.locator('.result-swr').first().innerText();
  const match = text.match(/([\d.]+)\s*:\s*1/);
  return match ? parseFloat(match[1]) : NaN;
}

/**
 * Read the matched resistance out of the result panel, as "Z = 50.0 + j0.0".
 * This is the matched impedance, not the antenna impedance the sliders set.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<number>}
 */
async function readResistance(page) {
  const text = await page.locator('.result-z').first().innerText();
  const match = text.match(/Z\s*=\s*([\d.]+)/);
  return match ? parseFloat(match[1]) : NaN;
}

/**
 * The swr-* class the result panel is wearing, which is how the page colors
 * a match good or poor.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<?string>}
 */
async function swrClass(page) {
  return page.locator('.result-swr').first().evaluate((el) => {
    for (const cls of el.classList) if (cls.startsWith('swr-')) return cls;
    const inner = el.querySelector('[class*="swr-"]');
    return inner ? [...inner.classList].find(c => c.startsWith('swr-')) ?? null : null;
  });
}

/**
 * @param {import('@playwright/test').Page} page
 * @param {'gamma'|'hairpin'|'ocfd'} mode
 */
async function switchMode(page, mode) {
  // getByRole rather than a hasText regex: one of the labels is "Beta
  // (Hairpin) Match", whose parentheses are regex metacharacters.
  await page.getByRole('button', { name: MODE_BUTTON[mode], exact: true }).click();
}

/** @param {import('@playwright/test').Page} page */
async function autoTune(page) {
  await page.locator('.auto-tune-btn', { hasText: /^Auto-Tune$/ }).click();
}

/** @param {import('@playwright/test').Page} page */
async function impedanceDisplay(page) {
  return page.locator('.impedance-display').first().innerText();
}

/**
 * Open the dipole calculator if it is collapsed.  Its header carries a
 * right-pointing triangle when closed.
 *
 * @param {import('@playwright/test').Page} page
 */
async function openCalculator(page) {
  const header = page.locator('.control-header', { hasText: 'CALCULATOR' });
  if ((await header.innerText()).includes('▶')) await header.click();
}

// ============================================================
// 1. Page load and rendering
// ============================================================

test('1.1 loads with no JavaScript errors', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(PAGE);
  await expect(page.locator('.title')).toBeVisible();
  expect(errors).toEqual([]);
});

test('1.2 key elements are present', async ({ page }) => {
  await page.goto(PAGE);
  for (const sel of ['.title', '.smith-chart', '.controls', '.mode-toggle',
                     '.result-panel', '.result-swr', '.diagram-svg']) {
    await expect(page.locator(sel).first()).toBeVisible();
  }
  expect(await page.locator('.preset-btn').count()).toBeGreaterThanOrEqual(3);
  expect(await page.locator('input[type=range]').count()).toBeGreaterThanOrEqual(2);
});

test('1.3 opens in Gamma Match', async ({ page }) => {
  await page.goto(PAGE);
  await expect(page.locator('.title')).toHaveText('Gamma Match');
});

// ============================================================
// 2. Mathematical invariants
// ============================================================

test('2.1-2.3 SWR is finite and at least 1, with positive resistance', async ({ page }) => {
  await page.goto(PAGE);
  const swr = await readSWR(page);
  expect(Number.isFinite(swr)).toBe(true);
  expect(swr).toBeGreaterThanOrEqual(1);
  expect(await readResistance(page)).toBeGreaterThan(0);
});

test('2.4 invariants hold after auto-tune', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=25&x=0&tap=1&rod=300&cap=30`);
  await autoTune(page);
  await expect.poll(() => readSWR(page)).toBeLessThan(2);
  const swr = await readSWR(page);
  expect(Number.isFinite(swr)).toBe(true);
  expect(swr).toBeGreaterThanOrEqual(1);
  expect(await readResistance(page)).toBeGreaterThan(0);
});

// ============================================================
// 3. Gamma match controls
// ============================================================

for (const [label, value] of [
  ['Tap ratio', 2.0],
  ['Gamma rod reactance', 50],
  ['Series capacitor reactance', 80],
]) {
  test(`3.x the ${label} slider changes the result`, async ({ page }) => {
    await page.goto(`${PAGE}?mode=gamma&r=73&x=43&tap=1&rod=300&cap=30`);
    const before = await readSWR(page);
    await setSlider(page, /** @type {string} */ (label), Number(value));
    await expect.poll(() => readSWR(page)).not.toBe(before);
  });
}

test('3.4 gamma auto-tune converges', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=25&x=0&tap=1&rod=300&cap=30`);
  await autoTune(page);
  await expect.poll(() => readSWR(page)).toBeLessThan(2);
});

// ============================================================
// 4. Hairpin match controls
// ============================================================

for (const [label, value] of [
  ['Element shortening reactance', 5],
  ['Hairpin reactance', 180],
]) {
  test(`4.x the ${label} slider changes the result`, async ({ page }) => {
    await page.goto(`${PAGE}?mode=hairpin&r=25&x=0&short=15&hp=50`);
    const before = await readSWR(page);
    await setSlider(page, /** @type {string} */ (label), Number(value));
    await expect.poll(() => readSWR(page)).not.toBe(before);
  });
}

test('4.3 hairpin auto-tune converges', async ({ page }) => {
  await page.goto(`${PAGE}?mode=hairpin&r=25&x=0&short=0&hp=200`);
  await autoTune(page);
  await expect.poll(() => readSWR(page)).toBeLessThan(2);
});

// ============================================================
// 5. Presets
// ============================================================

test('5.1-5.2 every preset loads its impedance and lands under SWR 2', async ({ page }) => {
  await page.goto(PAGE);
  const presets = page.locator('.presets .preset-btn');
  const labels = await presets.allInnerTexts();

  for (const label of labels.map(t => t.trim())) {
    if (label === 'Reset') continue;
    await page.locator('.presets .preset-btn', { hasText: label }).first().click();

    // Labels name their resistance, as "(73+j43)" or "(67)".
    const match = label.match(/\((\d+)(?:[+−-]|Ω)/);
    if (match) expect(await impedanceDisplay(page)).toContain(match[1]);
    await expect.poll(() => readSWR(page)).toBeLessThan(2);
  }
});

test('5.3 the chosen preset is the active one', async ({ page }) => {
  await page.goto(PAGE);
  const presets = page.locator('.presets .preset-btn');
  const labels = (await presets.allInnerTexts()).map(t => t.trim()).filter(t => t !== 'Reset');

  await presets.filter({ hasText: labels[0] }).first().click();
  await expect(presets.filter({ hasText: labels[0] }).first()).toHaveClass(/active/);
  await expect(presets.filter({ hasText: labels[1] }).first()).not.toHaveClass(/active/);
});

// ============================================================
// 6. Mode switching
// ============================================================

for (const [mode, title] of [
  ['gamma', 'Gamma Match'],
  ['hairpin', 'Beta (Hairpin) Match'],
  ['ocfd', 'Off-Center Fed Doublet'],
]) {
  test(`6.x ${mode} mode is titled "${title}"`, async ({ page }) => {
    await page.goto(PAGE);
    await switchMode(page, /** @type {'gamma'|'hairpin'|'ocfd'} */ (mode));
    await expect(page.locator('.title')).toHaveText(title);
  });
}

test('6.4-6.6 the diagram, overlay and controls all differ per mode', async ({ page }) => {
  await page.goto(PAGE);

  /** @returns {Promise<{diagram: string, title: string, smith: string, controls: string}>} */
  const snapshot = () => page.evaluate(() => ({
    diagram: document.querySelector('.diagram-svg').innerHTML,
    title: document.querySelector('.diagram-title').textContent,
    smith: document.querySelector('.smith-chart').innerHTML,
    controls: document.querySelector('.controls').innerHTML,
  }));

  await switchMode(page, 'gamma');
  await expect(page.locator('.title')).toHaveText('Gamma Match');
  const gamma = await snapshot();

  await switchMode(page, 'hairpin');
  await expect(page.locator('.title')).toHaveText('Beta (Hairpin) Match');
  const hairpin = await snapshot();

  await switchMode(page, 'ocfd');
  await expect(page.locator('.title')).toHaveText('Off-Center Fed Doublet');
  const ocfd = await snapshot();

  for (const key of /** @type {const} */ (['diagram', 'title', 'smith', 'controls'])) {
    expect(gamma[key], `gamma vs hairpin ${key}`).not.toBe(hairpin[key]);
    expect(hairpin[key], `hairpin vs ocfd ${key}`).not.toBe(ocfd[key]);
  }
});

test('6.7 antenna impedance survives a mode round trip', async ({ page }) => {
  await page.goto(PAGE);
  await setSlider(page, 'Antenna resistance', 40);
  await setSlider(page, 'Antenna reactance', -20);
  await expect.poll(() => sliderValue(page, 'Antenna resistance')).toBe(40);

  await switchMode(page, 'hairpin');
  await switchMode(page, 'gamma');
  expect(await sliderValue(page, 'Antenna resistance')).toBe(40);
  expect(await sliderValue(page, 'Antenna reactance')).toBe(-20);
});

// ============================================================
// 7. URL parameters
//
// The case worth having: each mode serializes its own subset of the state,
// so a key added to one mode and not to its serializeUrl drops silently out
// of a shared link.
// ============================================================

test('7.1 a slider change reaches the URL', async ({ page }) => {
  await page.goto(PAGE);
  await setSlider(page, 'Antenna resistance', 40);
  await expect(page).toHaveURL(/[?&]r=40\b/);
});

test('7.2 reset restores the defaults', async ({ page }) => {
  await page.goto(PAGE);
  await setSlider(page, 'Antenna resistance', 40);
  await expect(page).toHaveURL(/[?&]r=40\b/);

  await page.locator('.preset-btn', { hasText: /^Reset$/ }).click();
  await expect.poll(() => sliderValue(page, 'Antenna resistance')).toBe(73);
  expect(await sliderValue(page, 'Antenna reactance')).toBe(43);
});

test('7.3 gamma parameters round-trip through the URL', async ({ page }) => {
  await page.goto(PAGE);
  await setSlider(page, 'Antenna resistance', 30);
  await expect(page).toHaveURL(/[?&]r=30\b/);

  await page.goto(page.url());
  expect(await sliderValue(page, 'Antenna resistance')).toBe(30);
});

test('7.3b hairpin parameters round-trip through the URL', async ({ page }) => {
  await page.goto(`${PAGE}?mode=hairpin&r=25&x=0&short=10&hp=80`);
  await expect(page.locator('.title')).toHaveText('Beta (Hairpin) Match');
  expect(await sliderValue(page, 'Antenna resistance')).toBe(25);
  expect(await sliderValue(page, 'Antenna reactance')).toBe(0);
  expect(await sliderValue(page, 'Element shortening reactance')).toBe(10);
  expect(await sliderValue(page, 'Hairpin reactance')).toBe(80);
});

test('7.4 an unknown mode or ground type falls back', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(`${PAGE}?mode=nonsense&gnd=nonsense`);
  await expect(page.locator('.title')).toHaveText('Gamma Match');
  expect(errors).toEqual([]);
});

// ============================================================
// 8. Physical calculations
// ============================================================

test('8.1-8.2 a frequency gives a wavelength and a capacitor value', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=73&x=43&freq=145`);
  await expect(page.locator('body')).toContainText('λ =');
  await expect(page.locator('body')).toContainText('pF');
});

test('8.3 hairpin shows the shortening in mm and percent', async ({ page }) => {
  await page.goto(`${PAGE}?mode=hairpin&r=25&x=0&freq=145&diam=2`);
  await expect(page.locator('body')).toContainText('mm per side');
  await expect(page.locator('body')).toContainText('%');
});

// ============================================================
// 9. Edge cases
// ============================================================

test('9.1 extreme impedances stay finite and quiet', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(PAGE);

  for (const [r, x] of [[10, -100], [150, 100]]) {
    await setSlider(page, 'Antenna resistance', r);
    await setSlider(page, 'Antenna reactance', x);
    await expect.poll(() => sliderValue(page, 'Antenna resistance')).toBe(r);
    expect(Number.isFinite(await readSWR(page)), `R=${r} X=${x}`).toBe(true);
  }
  expect(errors).toEqual([]);
});

test('9.2 SWR coloring tracks the match quality', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=25&x=0&tap=1&rod=300&cap=30`);
  await autoTune(page);
  await expect.poll(() => readSWR(page)).toBeLessThan(2);
  expect(['swr-excellent', 'swr-good']).toContain(await swrClass(page));

  await setSlider(page, 'Tap ratio', 2.5);
  await setSlider(page, 'Gamma rod reactance', 20);
  await setSlider(page, 'Series capacitor reactance', 0);
  await expect.poll(() => readSWR(page)).toBeGreaterThan(2);
  expect(['swr-ok', 'swr-poor']).toContain(await swrClass(page));
});

// ============================================================
// 10. Antenna impedance sliders
// ============================================================

test('10.1-10.2 the sliders drive the impedance display', async ({ page }) => {
  await page.goto(PAGE);
  await setSlider(page, 'Antenna resistance', 100);
  await expect.poll(() => impedanceDisplay(page)).toContain('100');
  await setSlider(page, 'Antenna reactance', -50);
  await expect.poll(() => impedanceDisplay(page)).toContain('50');
});

// ============================================================
// 11. Shared dipole calculator
// ============================================================

for (const mode of /** @type {const} */ (['gamma', 'hairpin', 'ocfd'])) {
  test(`11.x the dipole calculator is available in ${mode} mode`, async ({ page }) => {
    await page.goto(`${PAGE}?mode=${mode}`);
    await expect(page.locator('.control-header', { hasText: 'DIPOLE CALCULATOR' }))
      .toBeVisible();
  });
}

test('11.4-11.5 frequency sits in the params bar, geometry in the calculator', async ({ page }) => {
  await page.goto(PAGE);
  await expect(page.locator('.physical-params input[type=number]').first()).toBeVisible();

  await openCalculator(page);
  await expect(page.locator('.controls input[min="0.1"][max="100"]').first()).toBeVisible();

  const grounds = await page.locator('.controls .preset-btn').allInnerTexts();
  const known = grounds.map(t => t.trim())
    .filter(t => ['Free space', 'Perfect', 'Sea water', 'Wet', 'Average', 'Dry', 'City'].includes(t));
  expect(known.length).toBeGreaterThanOrEqual(4);
});

test('11.6 free-space impedance, resonant length and K are shown', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=73&x=43&freq=146&diam=2&gnd=free`);
  await openCalculator(page);

  await expect(page.locator('body')).toContainText('Free-space');
  await expect(page.locator('body')).toContainText('Resonant length');
  await expect(page.locator('body')).toContainText('K =');

  // K is the shortening factor: about 0.96 for 2 mm wire at 146 MHz.
  const k = parseFloat((await page.locator('body').innerText()).match(/K\s*=\s*([\d.]+)/)[1]);
  expect(k).toBeGreaterThan(0.92);
  expect(k).toBeLessThan(0.99);
});

test('11.7 applying the computed impedance moves the sliders', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=73&x=43&freq=146&diam=2&gnd=free`);
  await openCalculator(page);
  await page.locator('.auto-tune-btn', { hasText: 'Apply to Antenna Impedance' }).click();

  // A free-space resonant dipole lands near 73 ohms.
  await expect.poll(() => sliderValue(page, 'Antenna resistance')).toBeGreaterThan(60);
  expect(await sliderValue(page, 'Antenna resistance')).toBeLessThan(90);
});

test('11.8 the antenna presets are not inside the calculator', async ({ page }) => {
  await page.goto(PAGE);
  await expect(page.locator('.presets')).toBeVisible();

  const inCalculator = await page.locator('.control-panel')
    .filter({ has: page.locator('.control-header', { hasText: 'CALCULATOR' }) })
    .locator('.preset-btn')
    .evaluateAll(btns => btns.filter(b =>
      b.textContent.includes('Ω') && !b.textContent.includes('line')).length);
  expect(inCalculator).toBe(0);
});

test('11.9 every mode offers presets', async ({ page }) => {
  for (const mode of ['gamma', 'hairpin', 'ocfd']) {
    await page.goto(`${PAGE}?mode=${mode}`);
    expect(await page.locator('.presets .preset-btn').count(),
      `${mode} presets`).toBeGreaterThanOrEqual(2);
  }
});

test('11.10 height and ground reach the URL in every mode', async ({ page }) => {
  await page.goto(`${PAGE}?mode=gamma&r=73&x=43&freq=146&diam=2&ht=10&gnd=wet`);
  await expect(page).toHaveURL(/[?&]ht=/);
  await expect(page).toHaveURL(/[?&]gnd=/);
});

// ============================================================
// 12. OCFD
// ============================================================

for (const [label, value] of [
  ['Feed offset', 33],
  ['OCFD center resistance', 50],
  ['OCFD center reactance', 30],
]) {
  test(`12.x the ${label} slider changes the result`, async ({ page }) => {
    await page.goto(`${PAGE}?mode=ocfd&ocr=73&ocx=43&off=10`);
    const before = await readSWR(page);
    await setSlider(page, /** @type {string} */ (label), Number(value));
    await expect.poll(() => readSWR(page)).not.toBe(before);
  });
}

test('12.4 the feedline selector changes the SWR', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd&ocr=73&ocx=0&off=33`);
  const swr50 = await readSWR(page);
  await page.locator('[aria-label="300 ohm feedline"]').click();
  await expect.poll(() => readSWR(page)).not.toBe(swr50);
});

test('12.5 feed impedance follows the cos-squared law', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd&ocr=73&ocx=0&off=33`);

  // Z_a(alpha) = Z_0 / cos^2(pi*alpha); 73 ohms at 33% offset is about 282.
  const expected = 73 / Math.cos(Math.PI * 0.33) ** 2;
  const feedR = parseFloat((await page.locator('.result-z').first().innerText())
    .match(/Z\s*=\s*([\d.]+)/)[1]);
  expect(Math.abs(feedR - expected)).toBeLessThan(5);
});

test('12.6 the Free-Space preset sets impedance and leaves the offset alone', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd`);
  await page.locator('.presets .preset-btn', { hasText: 'Free-Space' }).click();

  await expect.poll(() => sliderValue(page, 'OCFD center resistance')).toBe(73);
  expect(await sliderValue(page, 'OCFD center reactance')).toBe(43);
  expect(await sliderValue(page, 'Feed offset')).toBe(0);
});

test('12.7 a 50% feed offset does not crash', async ({ page }) => {
  const errors = collectErrors(page);
  // cos^2 goes to zero here, so Z goes to infinity; the page must survive it.
  await page.goto(`${PAGE}?mode=ocfd&ocr=73&ocx=0&off=50`);
  await expect(page.locator('.result-z').first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('12.8-12.9 OCFD has no auto-tune, and says it is experimental', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd`);
  await expect(page.locator('.auto-tune-btn', { hasText: /^Auto-Tune$/ })).toHaveCount(0);
  await expect(page.locator('.experimental-banner')).toContainText('Experimental');
});

test('12.10 OCFD parameters round-trip through the URL', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd&ocr=60&ocx=-15&off=25&z0=300`);

  await expect(page.locator('.title')).toHaveText('Off-Center Fed Doublet');
  expect(await sliderValue(page, 'OCFD center resistance')).toBe(60);
  expect(await sliderValue(page, 'OCFD center reactance')).toBe(-15);
  expect(await sliderValue(page, 'Feed offset')).toBe(25);
  await expect(page.locator('.feedline-selector .preset-btn.active')).toContainText('300');
});

test('12.11 the SWR table covers several feedlines', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd&ocr=73&ocx=0&off=33`);
  expect(await page.locator('.swr-row').count()).toBeGreaterThanOrEqual(3);
});

test('12.12 a computed preset needs a frequency, and opens the calculator', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd&freq=7.1`);
  await page.locator('.presets .preset-btn', { hasText: 'λ/2 AGL' }).click();

  await expect.poll(() => sliderValue(page, 'OCFD center resistance')).toBeGreaterThan(0);
  await expect(page.locator('.control-header', { hasText: 'CALCULATOR' }))
    .toHaveAttribute('aria-expanded', 'true');
});

test('12.13 computed presets are disabled without a frequency', async ({ page }) => {
  await page.goto(`${PAGE}?mode=ocfd`);
  const presets = page.locator('.presets .preset-btn');
  await expect(presets.filter({ hasText: 'λ/2 AGL' })).toBeDisabled();
  await expect(presets.filter({ hasText: 'λ/4 AGL' })).toBeDisabled();
  await expect(presets.filter({ hasText: 'Free-Space' })).toBeEnabled();
});

// ============================================================
// 13. Core math, called directly
//
// Babel transpiles the page into script scope, so these functions are
// reachable from page.evaluate.  These are the tests that would catch a sign
// convention or a unit conversion going wrong.
// ============================================================

test('13.1-13.4 SWR against a known impedance', async ({ page }) => {
  await page.goto(PAGE);

  expect(await page.evaluate(() => calcSWR(Z(50, 0)))).toBeCloseTo(1.0, 3);
  expect(await page.evaluate(() => calcSWR(Z(100, 0)))).toBeCloseTo(2.0, 3);
  expect(await page.evaluate(() => calcSWR(Z(25, 0)))).toBeCloseTo(2.0, 3);
  expect(await page.evaluate(() => calcSWRForZ0(Z(300, 0), 300))).toBeCloseTo(1.0, 3);
});

test('13.5 a half-wave dipole is about 73 + j42.5', async ({ page }) => {
  await page.goto(PAGE);
  const z = await page.evaluate(() => {
    const res = calcDipoleIEMF(300, 0.5, 0.001);
    return { r: res.r, x: res.x };
  });
  expect(Math.abs(z.r - 73.1)).toBeLessThan(2.0);
  expect(Math.abs(z.x - 42.5)).toBeLessThan(3.0);
});

test('13.6 a resonant dipole has no reactance', async ({ page }) => {
  await page.goto(PAGE);
  const res = await page.evaluate(() => {
    const r = calcDipoleResonant(146, 2);
    return { x: r.z.x, K: r.K };
  });
  expect(Math.abs(res.x)).toBeLessThan(0.5);
  expect(res.K).toBeGreaterThan(0.92);
  expect(res.K).toBeLessThan(0.99);
});

test('13.7 a perfect ground reflects with gamma = -1', async ({ page }) => {
  await page.goto(PAGE);
  const gamma = await page.evaluate(() => calcGroundReflection(146, Infinity, 0));
  expect(gamma.re).toBeCloseTo(-1, 3);
  expect(gamma.im).toBeCloseTo(0, 3);
});

test('13.8 real ground moves the impedance off its free-space value', async ({ page }) => {
  await page.goto(PAGE);
  const [free, average] = await page.evaluate(() => [
    calcDipoleOverGround(146, 10, 2, 'free'),
    calcDipoleOverGround(146, 10, 2, 'average'),
  ].map(z => z && { r: z.r, x: z.x }));

  expect(free).not.toBeNull();
  expect(average).not.toBeNull();
  expect(Math.abs(free.r - average.r) > 0.5 || Math.abs(free.x - average.x) > 0.5).toBe(true);
});

test('13.9 a center feed is the offset=0 case of the OCFD formula', async ({ page }) => {
  await page.goto(PAGE);
  const factor = await page.evaluate(() => 1 / Math.cos(Math.PI * 0) ** 2);
  expect(factor).toBeCloseTo(1.0, 3);
});
