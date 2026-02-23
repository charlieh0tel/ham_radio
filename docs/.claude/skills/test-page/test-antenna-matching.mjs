#!/usr/bin/env node

// Automated test suite for antenna-matching.html
// Implements the test plan in antenna-matching-tests.md
//
// Usage: node test-antenna-matching.mjs [PORT]
// Requires: puppeteer (npm install puppeteer)

import puppeteer from 'puppeteer';

const PORT = process.argv[2] || process.env.TEST_PORT || 8787;
const BASE = `http://localhost:${PORT}/antenna-matching.html`;

// ============================================================
// Test runner
// ============================================================

let passed = 0;
let failed = 0;
const failures = [];

function test(name, fn) {
  return fn().then(() => {
    passed++;
    console.log(`  ✓ ${name}`);
  }).catch(err => {
    failed++;
    failures.push({ name, error: err.message });
    console.log(`  ✗ ${name}`);
    console.log(`    ${err.message}`);
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

// ============================================================
// Helpers
// ============================================================

/** Parse SWR number from ".result-swr" text like "SWR = 1.234 : 1" */
async function parseSWR(page) {
  const text = await page.$eval('.result-swr', el => el.textContent);
  const match = text.match(/([\d.]+)\s*:\s*1/);
  if (!match) throw new Error(`Cannot parse SWR from: "${text}"`);
  return parseFloat(match[1]);
}

/** Parse resistance from ".result-z" text like "Z = 50.0 + j0.0 Ω" */
async function parseResistance(page) {
  const text = await page.$eval('.result-z', el => el.textContent);
  const match = text.match(/Z\s*=\s*([\d.]+)/);
  if (!match) throw new Error(`Cannot parse resistance from: "${text}"`);
  return parseFloat(match[1]);
}

/** Get the SWR color class */
async function getSWRClass(page) {
  return page.$eval('.result-swr', el => {
    for (const cls of el.classList) {
      if (cls.startsWith('swr-')) return cls;
    }
    return null;
  });
}

/** Check mathematical invariants: SWR >= 1, finite, resistance > 0 */
async function checkInvariants(page, label) {
  const swr = await parseSWR(page);
  assert(Number.isFinite(swr), `${label}: SWR is not finite (${swr})`);
  assert(swr >= 1.0, `${label}: SWR < 1 (${swr})`);
  const r = await parseResistance(page);
  assert(r > 0, `${label}: resistance <= 0 (${r})`);
}

/** Set a range slider by aria-label to a specific value */
async function setSlider(page, ariaLabel, value) {
  await page.$eval(
    `input[aria-label="${ariaLabel}"]`,
    (slider, val) => {
      const nativeSet = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, 'value'
      ).set;
      nativeSet.call(slider, val);
      slider.dispatchEvent(new Event('input', { bubbles: true }));
      slider.dispatchEvent(new Event('change', { bubbles: true }));
    },
    value
  );
  await wait(page, 100);
}

/** Get current slider value by aria-label */
async function getSliderValue(page, ariaLabel) {
  return page.$eval(
    `input[aria-label="${ariaLabel}"]`,
    slider => Number(slider.value)
  );
}

/** Click auto-tune and wait for update */
async function autoTune(page) {
  await page.click('.auto-tune-btn');
  await wait(page, 300);
}

/** Click a mode button (1 = Gamma, 2 = Hairpin) */
async function switchMode(page, n) {
  await page.click(`.mode-btn:nth-child(${n})`);
  await wait(page, 300);
}

/** Read impedance display text */
async function getImpedanceDisplay(page) {
  return page.$eval('.impedance-display', el => el.textContent);
}

/** Short wait */
async function wait(page, ms = 200) {
  await new Promise(r => setTimeout(r, ms));
}

// ============================================================
// Main test suite
// ============================================================

async function run() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const errors = [];

  try {
    // ----------------------------------------------------------
    // 1. Page Load & Rendering
    // ----------------------------------------------------------
    console.log('\n1. Page Load & Rendering');

    let page = await browser.newPage();
    page.on('console', msg => {
      if (msg.type() === 'error'
        && !msg.text().includes('favicon')
        && !msg.text().includes('Failed to load resource')) {
        errors.push(msg.text());
      }
    });
    page.on('pageerror', err => errors.push(err.toString()));

    await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
    await wait(page, 500);

    await test('1.1 No JavaScript errors', async () => {
      assert(errors.length === 0, `Console errors: ${errors.join('; ')}`);
    });

    await test('1.2 Key elements present', async () => {
      const checks = await page.$eval('body', body => ({
        title: !!body.querySelector('.title'),
        smithChart: !!body.querySelector('.smith-chart'),
        controls: !!body.querySelector('.controls'),
        modeToggle: !!body.querySelector('.mode-toggle'),
        resultPanel: !!body.querySelector('.result-panel'),
        resultSwr: !!body.querySelector('.result-swr'),
        diagramSvg: !!body.querySelector('.diagram-svg'),
        presets: body.querySelectorAll('.preset-btn').length,
        sliders: body.querySelectorAll('input[type=range]').length,
      }));
      assert(checks.title, 'Missing .title');
      assert(checks.smithChart, 'Missing .smith-chart');
      assert(checks.controls, 'Missing .controls');
      assert(checks.modeToggle, 'Missing .mode-toggle');
      assert(checks.resultPanel, 'Missing .result-panel');
      assert(checks.resultSwr, 'Missing .result-swr');
      assert(checks.diagramSvg, 'Missing .diagram-svg');
      assert(checks.presets >= 3, `Only ${checks.presets} preset buttons`);
      assert(checks.sliders >= 2, `Only ${checks.sliders} sliders`);
    });

    await test('1.3 Initial title is Gamma Match', async () => {
      const title = await page.$eval('.title', el => el.textContent);
      assert(title.includes('Gamma Match'), `Title is "${title}"`);
    });

    // ----------------------------------------------------------
    // 2. Mathematical Invariants
    // ----------------------------------------------------------
    console.log('\n2. Mathematical Invariants');

    await test('2.1 SWR >= 1', async () => {
      const swr = await parseSWR(page);
      assert(swr >= 1.0, `SWR is ${swr}`);
    });

    await test('2.2 SWR is finite', async () => {
      const swr = await parseSWR(page);
      assert(Number.isFinite(swr), `SWR is ${swr}`);
    });

    await test('2.3 Resistance > 0', async () => {
      const r = await parseResistance(page);
      assert(r > 0, `Resistance is ${r}`);
    });

    await test('2.4 Invariants hold after auto-tune', async () => {
      await autoTune(page);
      await checkInvariants(page, 'after auto-tune');
    });

    // ----------------------------------------------------------
    // 3. Gamma Match Controls
    // ----------------------------------------------------------
    console.log('\n3. Gamma Match Controls');

    await test('3.1 Tap ratio slider changes results', async () => {
      const swr1 = await parseSWR(page);
      await setSlider(page, 'Tap ratio', 2.0);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR unchanged: ${swr1}`);
    });

    await test('3.2 Gamma rod slider changes results', async () => {
      const swr1 = await parseSWR(page);
      await setSlider(page, 'Gamma rod reactance', 50);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR unchanged: ${swr1}`);
    });

    await test('3.3 Series capacitor slider changes results', async () => {
      const swr1 = await parseSWR(page);
      await setSlider(page, 'Series capacitor reactance', 80);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR unchanged: ${swr1}`);
    });

    await test('3.4 Auto-tune converges (SWR < 2)', async () => {
      await autoTune(page);
      const swr = await parseSWR(page);
      assert(swr < 2.0, `SWR after auto-tune: ${swr}`);
    });

    // ----------------------------------------------------------
    // 4. Hairpin Match Controls
    // ----------------------------------------------------------
    console.log('\n4. Hairpin Match Controls');

    await switchMode(page, 2); // switch to Hairpin

    await test('4.1 Shortening slider changes results', async () => {
      await autoTune(page);
      const swr1 = await parseSWR(page);
      await setSlider(page, 'Element shortening reactance', 5);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR unchanged: ${swr1}`);
    });

    await test('4.2 Hairpin slider changes results', async () => {
      const swr1 = await parseSWR(page);
      await setSlider(page, 'Hairpin reactance', 180);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR unchanged: ${swr1}`);
    });

    await test('4.3 Auto-tune converges (SWR < 2)', async () => {
      await autoTune(page);
      const swr = await parseSWR(page);
      assert(swr < 2.0, `SWR after auto-tune: ${swr}`);
    });

    // ----------------------------------------------------------
    // 5. Presets
    // ----------------------------------------------------------
    console.log('\n5. Presets');

    await switchMode(page, 1); // back to Gamma

    const presetLabels = await page.$$eval('.preset-btn', btns =>
      btns.map(b => b.textContent)
    );

    for (let i = 0; i < presetLabels.length; i++) {
      const label = presetLabels[i];
      // Skip non-antenna-preset buttons (Auto-Tune, Copy URL, Reset)
      if (!label.includes('Ω')) continue;

      await test(`5.1.${i + 1} Preset "${label}" loads correct impedance`, async () => {
        await page.click(`.preset-btn:nth-child(${i + 1})`);
        await wait(page, 300);
        const display = await getImpedanceDisplay(page);
        // Extract R from the preset label, e.g. "(73+j43Ω)" or "(25Ω)"
        const match = label.match(/(\d+)[+−\-]/);
        if (match) {
          const expectedR = match[1];
          assert(display.includes(expectedR), `Impedance "${display}" doesn't contain R=${expectedR}`);
        }
      });

      await test(`5.2.${i + 1} Preset "${label}" auto-tunes`, async () => {
        const swr = await parseSWR(page);
        assert(swr < 2.0, `SWR after preset: ${swr}`);
      });
    }

    await test('5.3 Active state on preset button', async () => {
      await page.click('.preset-btn:nth-child(1)');
      await wait(page, 300);
      const hasActive = await page.$eval('.preset-btn:nth-child(1)', el =>
        el.classList.contains('active')
      );
      assert(hasActive, 'First preset button does not have .active class');
      const secondActive = await page.$eval('.preset-btn:nth-child(2)', el =>
        el.classList.contains('active')
      );
      assert(!secondActive, 'Second preset button incorrectly has .active class');
    });

    // ----------------------------------------------------------
    // 6. Mode Switching
    // ----------------------------------------------------------
    console.log('\n6. Mode Switching');

    await test('6.1 Gamma mode title', async () => {
      await switchMode(page, 1);
      const title = await page.$eval('.title', el => el.textContent);
      assert(title === 'Gamma Match', `Title is "${title}"`);
    });

    await test('6.2 Hairpin mode title', async () => {
      await switchMode(page, 2);
      const title = await page.$eval('.title', el => el.textContent);
      assert(title === 'Beta (Hairpin) Match', `Title is "${title}"`);
    });

    await test('6.3 Antenna impedance preserved across mode switch', async () => {
      await switchMode(page, 1); // Gamma
      await setSlider(page, 'Antenna resistance', 40);
      await setSlider(page, 'Antenna reactance', -20);
      const r1 = await getSliderValue(page, 'Antenna resistance');
      const x1 = await getSliderValue(page, 'Antenna reactance');
      await switchMode(page, 2); // Hairpin
      await switchMode(page, 1); // back to Gamma
      const r2 = await getSliderValue(page, 'Antenna resistance');
      const x2 = await getSliderValue(page, 'Antenna reactance');
      assert(r1 === r2, `R changed: ${r1} → ${r2}`);
      assert(x1 === x2, `X changed: ${x1} → ${x2}`);
    });

    // ----------------------------------------------------------
    // 7. URL Parameters
    // ----------------------------------------------------------
    console.log('\n7. URL Parameters');

    await test('7.1 URL updates on slider change', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      await setSlider(page, 'Antenna resistance', 40);
      await wait(page, 200);
      const search = await page.url();
      assert(search.includes('?'), 'URL has no query params after slider change');
    });

    await test('7.2 Reset restores defaults', async () => {
      await setSlider(page, 'Antenna resistance', 40);
      await wait(page, 200);
      // Reset navigates to bare pathname; auto-tune fires on fresh load adding params
      await Promise.all([
        page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }),
        page.$$eval('.preset-btn', btns => {
          const reset = btns.find(b => b.textContent.trim() === 'Reset');
          if (reset) reset.click();
        })
      ]);
      await wait(page, 500);
      // Verify antenna impedance is back to defaults (R=73, X=43)
      const r = await getSliderValue(page, 'Antenna resistance');
      const x = await getSliderValue(page, 'Antenna reactance');
      assert(r === 73, `R after reset: ${r}, expected 73`);
      assert(x === 43, `X after reset: ${x}, expected 43`);
    });

    await test('7.3 Round-trip from URL', async () => {
      await page.goto(`${BASE}?mode=hairpin&r=25&x=0&short=10&hp=80`, {
        waitUntil: 'networkidle0',
        timeout: 15000
      });
      await wait(page, 500);
      const title = await page.$eval('.title', el => el.textContent);
      assert(title === 'Beta (Hairpin) Match', `Title is "${title}"`);
      const r = await getSliderValue(page, 'Antenna resistance');
      const x = await getSliderValue(page, 'Antenna reactance');
      assert(r === 25, `R is ${r}, expected 25`);
      assert(x === 0, `X is ${x}, expected 0`);
      const short = await getSliderValue(page, 'Element shortening reactance');
      const hp = await getSliderValue(page, 'Hairpin reactance');
      assert(short === 10, `Shortening is ${short}, expected 10`);
      assert(hp === 80, `Hairpin is ${hp}, expected 80`);
    });

    // ----------------------------------------------------------
    // 8. Physical Calculations
    // ----------------------------------------------------------
    console.log('\n8. Physical Calculations');

    await test('8.1 Wavelength displayed with frequency', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      // Type frequency into the freq input
      const freqInput = await page.$('input[type=number][min="1"]');
      await freqInput.click({ clickCount: 3 });
      await freqInput.type('145');
      await wait(page, 300);
      const text = await page.$eval('body', body => body.innerText);
      assert(text.includes('λ ='), 'Wavelength not displayed');
    });

    await test('8.2 Capacitor pF shown in Gamma mode', async () => {
      await switchMode(page, 1);
      await wait(page, 200);
      const text = await page.$eval('body', body => body.innerText);
      assert(text.includes('pF'), 'pF not shown in Gamma mode with frequency set');
    });

    await test('8.3 Shortening mm/% shown in Hairpin mode', async () => {
      await switchMode(page, 2);
      await wait(page, 200);
      const text = await page.$eval('body', body => body.innerText);
      assert(text.includes('mm per side'), 'Shortening mm not shown');
      assert(text.includes('%'), 'Shortening % not shown');
    });

    // ----------------------------------------------------------
    // 9. Edge Cases
    // ----------------------------------------------------------
    console.log('\n9. Edge Cases');

    await test('9.1 Extreme slider values don\'t crash', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      const errorsBefore = errors.length;

      await setSlider(page, 'Antenna resistance', 10);
      await setSlider(page, 'Antenna reactance', -100);
      await wait(page, 200);
      let swr = await parseSWR(page);
      assert(Number.isFinite(swr), `SWR not finite at R=10,X=-100: ${swr}`);

      await setSlider(page, 'Antenna resistance', 150);
      await setSlider(page, 'Antenna reactance', 100);
      await wait(page, 200);
      swr = await parseSWR(page);
      assert(Number.isFinite(swr), `SWR not finite at R=150,X=100: ${swr}`);

      assert(errors.length === errorsBefore, 'New console errors at extremes');
    });

    await test('9.2 SWR color classes', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      await autoTune(page);
      const goodClass = await getSWRClass(page);
      assert(
        goodClass === 'swr-excellent' || goodClass === 'swr-good',
        `After auto-tune, expected swr-excellent or swr-good, got ${goodClass}`
      );

      // Detune to get poor SWR
      await setSlider(page, 'Tap ratio', 2.5);
      await setSlider(page, 'Gamma rod reactance', 20);
      await setSlider(page, 'Series capacitor reactance', 0);
      await wait(page, 200);
      const swr = await parseSWR(page);
      if (swr > 2.0) {
        const poorClass = await getSWRClass(page);
        assert(poorClass === 'swr-poor' || poorClass === 'swr-ok',
          `Expected swr-poor or swr-ok for SWR=${swr}, got ${poorClass}`);
      }
    });

    // ----------------------------------------------------------
    // 10. Antenna Impedance Sliders
    // ----------------------------------------------------------
    console.log('\n10. Antenna Impedance Sliders');

    await test('10.1 Resistance slider updates display', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      await setSlider(page, 'Antenna resistance', 100);
      await wait(page, 200);
      const display = await getImpedanceDisplay(page);
      assert(display.includes('100'), `Display "${display}" doesn't show R=100`);
    });

    await test('10.2 Reactance slider updates display', async () => {
      await setSlider(page, 'Antenna reactance', -50);
      await wait(page, 200);
      const display = await getImpedanceDisplay(page);
      assert(display.includes('50'), `Display "${display}" doesn't show X=50`);
    });

    await page.close();
  } finally {
    await browser.close();
  }

  // ----------------------------------------------------------
  // Summary
  // ----------------------------------------------------------
  console.log('\n' + '='.repeat(50));
  console.log(`Results: ${passed} passed, ${failed} failed, ${passed + failed} total`);
  if (failures.length > 0) {
    console.log('\nFailures:');
    for (const f of failures) {
      console.log(`  ✗ ${f.name}: ${f.error}`);
    }
  }
  console.log('='.repeat(50));

  process.exit(failed > 0 ? 1 : 0);
}

run().catch(err => {
  console.error('Test runner crashed:', err);
  process.exit(2);
});
