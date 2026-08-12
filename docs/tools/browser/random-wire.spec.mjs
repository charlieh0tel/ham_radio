/**
 * Browser checks for random-wire.html.
 *
 * These exist because the type checker proves the page compiles and the
 * node tests prove the DOM-free half computes, and neither can see a
 * control that does not render, a button that activates the wrong thing,
 * or text that has become unreadable.  Every test here corresponds to an
 * item in RANDOM_WIRE_BROWSER_CHECKS.md.
 *
 * Assertions are on behaviour and invariants rather than on fixed values,
 * so that changing a coefficient or a default does not break the suite.
 */

import { expect, test } from '@playwright/test';

/** SWR the page promises to stay within, per tuner button. */
const TUNER_LIMITS = { '3:1': 3, '5:1': 5, '9:1': 9, '12:1': 12 };

/** Feet per metre, for the legacy URL parameter check. */
const FEET_PER_METRE = 1 / 0.3048;

/**
 * A control group, addressed by its legend.  Scoping matters: "9:1" is an
 * option in both the Tuner and the Unun ratio groups.
 * @param {import('@playwright/test').Page} page
 * @param {string} legend
 */
const group = (page, legend) =>
  page.locator('fieldset', {
    has: page.locator('legend', { hasText: new RegExp(`^\\s*${legend}\\s*$`) }),
  });

/**
 * One option within a group, by its exact label.  These are buttons
 * carrying role="radio" and aria-checked, so getByRole('button') does not
 * find them.  Text is matched exactly because "1:1" is a substring of
 * "11:1".
 * @param {import('@playwright/test').Page} page
 * @param {string} legend
 * @param {string} label
 */
const option = (page, legend, label) =>
  group(page, legend).locator(`button:text-is("${label}")`);

/**
 * Open the page and wait for React to have rendered.
 * @param {import('@playwright/test').Page} page
 * @param {string} query
 * @returns {Promise<string[]>} console errors seen, which should stay empty
 */
async function open(page, query = '?mode=impedance') {
  /** @type {string[]} */
  const errors = [];
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(String(error)));
  await page.goto(`/random-wire.html${query}`);
  await page.getByRole('heading', { level: 1 }).waitFor();
  return errors;
}

/** The scored table of published lengths, as [length, average, worst, verdict]. */
async function publishedLengths(page) {
  return page.evaluate(() => {
    const table = [...document.querySelectorAll('table')].find((candidate) =>
      [...candidate.querySelectorAll('th')].some((th) =>
        th.textContent.includes('Verdict'),
      ),
    );
    return [...table.querySelectorAll('tbody tr')].map((row) =>
      [...row.cells].map((cell) => cell.textContent.trim()),
    );
  });
}

/** Which option in a group is selected, per its own ARIA state. */
const selected = (page, legend) =>
  group(page, legend).locator('button[aria-checked="true"]').first().textContent();

/** The wire length the page currently holds, in whatever unit is displayed. */
const lengthField = (page) => page.locator('input[type=number]');

/** Relative luminance of an "rgb(r, g, b)" string, per WCAG 2.1. */
function luminance(colour) {
  const [r, g, b] = colour.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number);
  const channel = (value) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** WCAG contrast ratio between two "rgb(...)" strings. */
function contrast(foreground, background) {
  const a = luminance(foreground);
  const b = luminance(background);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

test.describe('loading', () => {
  for (const mode of ['impedance', 'classical']) {
    test(`${mode} mode loads with a clean console`, async ({ page }) => {
      const errors = await open(page, `?mode=${mode}`);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      expect(errors).toEqual([]);
    });
  }
});

test.describe('control groups', () => {
  // A <label> wrapping a group of buttons activates the first of them, so
  // these are fieldsets with legends instead.  A legend activates nothing.
  for (const legend of ['Ground', 'Tuner', 'Unun ratio']) {
    test(`clicking the ${legend} legend selects nothing`, async ({ page }) => {
      await open(page);
      const before = await selected(page, legend);
      await group(page, legend).locator('legend').click();
      expect(await selected(page, legend)).toBe(before);
    });
  }

  test('each group has exactly one selection', async ({ page }) => {
    await open(page);
    for (const legend of ['Units', 'Ground', 'Tuner', 'Unun ratio']) {
      await expect(
        group(page, legend).locator('button[aria-checked="true"]'),
      ).toHaveCount(1);
    }
  });
});

test.describe('the tuner decides the verdicts', () => {
  test('a length is ok exactly when its worst band is within the limit', async ({
    page,
  }) => {
    await open(page);
    for (const [button, limit] of Object.entries(TUNER_LIMITS)) {
      await option(page, 'Tuner', button).click();
      await expect(option(page, 'Tuner', button)).toHaveAttribute(
        'aria-checked',
        'true',
      );
      const rows = await publishedLengths(page);
      expect(rows.length).toBeGreaterThan(0);
      for (const [length, , worst, verdict] of rows) {
        const swr = Number.parseFloat(worst);
        expect(
          verdict,
          `${length} worst ${worst} against a ${button} tuner`,
        ).toBe(swr <= limit ? 'ok' : 'poor');
      }
    }
  });

  test('a stricter tuner accepts a subset, never different lengths', async ({
    page,
  }) => {
    await open(page);
    /** @type {string[][]} */
    const accepted = [];
    for (const button of Object.keys(TUNER_LIMITS)) {
      await option(page, 'Tuner', button).click();
      await expect(option(page, 'Tuner', button)).toHaveAttribute(
        'aria-checked',
        'true',
      );
      const rows = await publishedLengths(page);
      accepted.push(rows.filter((row) => row[3] === 'ok').map((row) => row[0]));
    }
    for (let i = 1; i < accepted.length; i += 1) {
      for (const length of accepted[i - 1]) {
        expect(accepted[i], `${length} accepted by a stricter tuner`).toContain(
          length,
        );
      }
    }
  });
});

test.describe('the installation panel', () => {
  test('the quarter-wave preset sets a quarter wave, not that plus the drop', async ({
    page,
  }) => {
    await open(page);
    await page.locator('button', { hasText: /λ\/4 on/ }).first().click();
    const label = await page.locator('label', { hasText: 'Counterpoise' }).textContent();
    const feet = Number.parseFloat(label.match(/([\d.]+)\s*ft/)[1]);
    // A quarter wave on 40 m is about 35 ft.  Adding the wire height on top
    // would put it near 65.
    expect(feet).toBeGreaterThan(32);
    expect(feet).toBeLessThan(38);
  });

  test('every part of the return slider changes the return', async ({ page }) => {
    await open(page);
    const returnPath = page
      .locator('label', { hasText: 'Counterpoise' })
      .locator('input');
    const readout = async () =>
      Number.parseFloat(
        (await page.locator('label', { hasText: 'Counterpoise' }).textContent()).match(
          /([\d.]+)\s*ft/,
        )[1],
      );

    const min = Number(await returnPath.getAttribute('min'));
    const max = Number(await returnPath.getAttribute('max'));
    const step = Number(await returnPath.getAttribute('step'));
    // A range input steps from its own min, so only those values are legal.
    const snap = (value) => min + Math.round((value - min) / step) * step;

    // Anywhere the thumb can go, moving it must move the number.  A floor
    // below the wire height would leave the bottom of the travel inert.
    const seen = new Set();
    for (const fraction of [0, 0.25, 0.5, 0.75, 1]) {
      await returnPath.fill(String(snap(min + (max - min) * fraction)));
      seen.add(await readout());
    }
    expect(seen.size).toBe(5);
  });

  test('the return path is never shorter than the drop it starts with', async ({
    page,
  }) => {
    await open(page);
    const height = page.locator('label', { hasText: 'Wire height' }).locator('input');
    const returnPath = page
      .locator('label', { hasText: 'Counterpoise' })
      .locator('input');
    // Set a short return, then raise the wire above it.  The return has to
    // follow, because the drop is part of it.
    await returnPath.fill(await returnPath.getAttribute('min'));
    await height.fill('25');
    const readout = await page
      .locator('label', { hasText: 'Counterpoise' })
      .textContent();
    const returnFeet = Number.parseFloat(readout.match(/([\d.]+)\s*ft/)[1]);
    const heightFeet = Number.parseFloat(
      (await page.locator('label', { hasText: 'Wire height' }).textContent()).match(
        /([\d.]+)\s*ft/,
      )[1],
    );
    expect(returnFeet).toBeGreaterThanOrEqual(heightFeet - 0.1);
  });
});

test.describe('the length field', () => {
  test('a typed length survives a change of display units', async ({ page }) => {
    await open(page);
    await lengthField(page).fill('71');
    await lengthField(page).blur();
    await option(page, 'Units', 'meters').click();
    await option(page, 'Units', 'feet').click();
    expect(Number.parseFloat(await lengthField(page).inputValue())).toBeCloseTo(71, 1);
  });

  test('a partial entry does not blank the field', async ({ page }) => {
    await open(page);
    await lengthField(page).fill('5.');
    expect(await lengthField(page).inputValue()).not.toBe('');
  });
});

test.describe('URLs', () => {
  test('the page comes back the same from its own URL', async ({ page }) => {
    await open(page);
    await option(page, 'Tuner', '9:1').click();
    await option(page, 'Ground', 'Damp').click();
    await lengthField(page).fill('84');
    await lengthField(page).blur();
    await page.waitForFunction(() => window.location.search.length > 1);

    const url = page.url();
    const before = await publishedLengths(page);
    await page.goto(url);
    await page.getByRole('heading', { level: 1 }).waitFor();

    expect(await selected(page, 'Tuner')).toBe('9:1');
    expect(await selected(page, 'Ground')).toBe('Damp');
    expect(await publishedLengths(page)).toEqual(before);
  });

  test('the legacy ?len= is still read as feet', async ({ page }) => {
    await open(page, '?mode=impedance&len=70');
    const legacy = await lengthField(page).inputValue();
    await open(page, `?mode=impedance&len_m=${(70 / FEET_PER_METRE).toFixed(4)}`);
    expect(Number.parseFloat(await lengthField(page).inputValue())).toBeCloseTo(
      Number.parseFloat(legacy),
      1,
    );
  });
});

test.describe('layout and legibility', () => {
  test('the experimental ribbon scrolls away with the page', async ({ page }) => {
    await open(page);
    const ribbon = page.getByText('EXPERIMENTAL').first();
    const position = await ribbon.evaluate((node) => getComputedStyle(node).position);
    expect(['fixed', 'sticky']).not.toContain(position);
  });

  test('nothing scrolls sideways at phone width', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await open(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('small print stays readable against its background', async ({ page }) => {
    await open(page);
    const failures = await page.evaluate(() => {
      /** Walk up for the first ancestor that actually paints a background. */
      const backgroundOf = (node) => {
        for (let el = node; el; el = el.parentElement) {
          const colour = getComputedStyle(el).backgroundColor;
          if (colour && colour !== 'rgba(0, 0, 0, 0)' && colour !== 'transparent') {
            return colour;
          }
        }
        return 'rgb(0, 0, 0)';
      };
      const out = [];
      for (const el of document.querySelectorAll('p, span, div, small, label')) {
        const style = getComputedStyle(el);
        const size = Number.parseFloat(style.fontSize);
        const text = [...el.childNodes]
          .filter((n) => n.nodeType === Node.TEXT_NODE)
          .map((n) => n.textContent.trim())
          .join('');
        if (!text || size > 13.5 || el.offsetParent === null) continue;
        out.push({ text: text.slice(0, 40), size, fg: style.color, bg: backgroundOf(el) });
      }
      return out;
    });

    expect(failures.length).toBeGreaterThan(0);
    for (const item of failures) {
      expect(
        contrast(item.fg, item.bg),
        `${item.size}px text "${item.text}"`,
      ).toBeGreaterThanOrEqual(4.5);
    }
  });
});

test.describe('keyboard', () => {
  test('a suggested length can be taken with the keyboard alone', async ({ page }) => {
    await open(page);
    // A RegExp rather than a :text-matches() string: Playwright unescapes the
    // quoted pattern in that selector, so "\d" would arrive as a literal "d".
    const suggestion = page
      .getByRole('button', { name: /^\d+(\.\d+)? ft$/ })
      .first();
    await suggestion.focus();
    await expect(suggestion).toBeFocused();
    const wanted = Number.parseFloat(await suggestion.textContent());
    await page.keyboard.press('Enter');
    expect(Number.parseFloat(await lengthField(page).inputValue())).toBeCloseTo(
      wanted,
      1,
    );
  });

  test('focus is visible on the control that has it', async ({ page }) => {
    await open(page);
    const button = option(page, 'Tuner', '9:1');
    await button.focus();
    const ring = await button.evaluate((node) => {
      const style = getComputedStyle(node);
      return {
        outlineWidth: style.outlineWidth,
        outlineStyle: style.outlineStyle,
        boxShadow: style.boxShadow,
      };
    });
    const hasRing =
      (ring.outlineStyle !== 'none' && Number.parseFloat(ring.outlineWidth) > 0) ||
      (ring.boxShadow && ring.boxShadow !== 'none');
    expect(hasRing, JSON.stringify(ring)).toBe(true);
  });
});
