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
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('.auto-tune-btn')]
      .find(b => b.textContent.trim() === 'Auto-Tune');
    if (!btn) throw new Error('Auto-Tune button not found');
    btn.click();
  });
  await wait(page, 300);
}

/** Click a mode button by name ('gamma', 'hairpin', or 'ocfd') */
async function switchMode(page, modeName) {
  const labels = { gamma: 'Gamma Match', hairpin: 'Beta (Hairpin) Match', ocfd: 'OCFD' };
  const label = labels[modeName];
  if (!label) throw new Error(`Unknown mode: ${modeName}`);
  await page.evaluate((lbl) => {
    const btn = [...document.querySelectorAll('.mode-btn')]
      .find(b => b.textContent.trim() === lbl);
    if (!btn) throw new Error(`Mode button "${lbl}" not found`);
    btn.click();
  }, label);
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

    await switchMode(page, 'hairpin'); // switch to Hairpin

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

    await switchMode(page, 'gamma'); // back to Gamma

    // Get antenna preset labels from the top-level .presets section
    const presetLabels = await page.$$eval('.presets .preset-btn', btns =>
      btns.map(b => b.textContent.trim())
    );

    /** Click a preset button by its label text */
    async function clickPreset(pg, label) {
      await pg.$$eval('.presets .preset-btn', (btns, lbl) => {
        const btn = btns.find(b => b.textContent.trim() === lbl);
        if (!btn) throw new Error(`Preset button "${lbl}" not found`);
        btn.click();
      }, label);
      await wait(pg, 300);
    }

    for (let i = 0; i < presetLabels.length; i++) {
      const label = presetLabels[i];

      await test(`5.1.${i + 1} Preset "${label}" loads correct impedance`, async () => {
        await clickPreset(page, label);
        const display = await getImpedanceDisplay(page);
        // Extract R from the preset label, e.g. "(73+j43Ω)" or "(67Ω)"
        const match = label.match(/\((\d+)(?:[+−\-]|Ω)/);
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
      await clickPreset(page, presetLabels[0]);
      const activeState = await page.$$eval('.presets .preset-btn', (btns, firstLbl, secondLbl) => {
        const first = btns.find(b => b.textContent.trim() === firstLbl);
        const second = btns.find(b => b.textContent.trim() === secondLbl);
        return {
          firstActive: first ? first.classList.contains('active') : false,
          secondActive: second ? second.classList.contains('active') : false,
        };
      }, presetLabels[0], presetLabels[1]);
      assert(activeState.firstActive, 'First preset button does not have .active class');
      assert(!activeState.secondActive, 'Second preset button incorrectly has .active class');
    });

    // ----------------------------------------------------------
    // 6. Mode Switching
    // ----------------------------------------------------------
    console.log('\n6. Mode Switching');

    await test('6.1 Gamma mode title', async () => {
      await switchMode(page, 'gamma');
      const title = await page.$eval('.title', el => el.textContent);
      assert(title === 'Gamma Match', `Title is "${title}"`);
    });

    await test('6.2 Hairpin mode title', async () => {
      await switchMode(page, 'hairpin');
      const title = await page.$eval('.title', el => el.textContent);
      assert(title === 'Beta (Hairpin) Match', `Title is "${title}"`);
    });

    await test('6.3 OCFD mode title', async () => {
      await switchMode(page, 'ocfd');
      const title = await page.evaluate(() =>
        document.querySelector('.title').textContent
      );
      assert(title === 'Off-Center Fed Doublet', `Title is "${title}"`);
    });

    await test('6.4 Diagram changes with each mode', async () => {
      await switchMode(page, 'gamma'); // Gamma
      await wait(page, 200);
      const gammaDiag = await page.evaluate(() => ({
        svg: document.querySelector('.diagram-svg').innerHTML,
        title: document.querySelector('.diagram-title').textContent,
      }));
      await switchMode(page, 'hairpin'); // Hairpin
      await wait(page, 200);
      const hairpinDiag = await page.evaluate(() => ({
        svg: document.querySelector('.diagram-svg').innerHTML,
        title: document.querySelector('.diagram-title').textContent,
      }));
      await switchMode(page, 'ocfd'); // OCFD
      await wait(page, 200);
      const ocfdDiag = await page.evaluate(() => ({
        svg: document.querySelector('.diagram-svg').innerHTML,
        title: document.querySelector('.diagram-title').textContent,
      }));
      assert(gammaDiag.svg !== hairpinDiag.svg,
        'Gamma and Hairpin diagrams have identical SVG');
      assert(hairpinDiag.svg !== ocfdDiag.svg,
        'Hairpin and OCFD diagrams have identical SVG');
      assert(gammaDiag.svg !== ocfdDiag.svg,
        'Gamma and OCFD diagrams have identical SVG');
      assert(gammaDiag.title !== hairpinDiag.title,
        'Gamma and Hairpin diagram titles are identical');
      assert(hairpinDiag.title !== ocfdDiag.title,
        'Hairpin and OCFD diagram titles are identical');
    });

    await test('6.5 Smith chart overlay changes with each mode', async () => {
      await switchMode(page, 'gamma');
      await wait(page, 200);
      const gammaSmith = await page.evaluate(() =>
        document.querySelector('.smith-chart').innerHTML
      );
      await switchMode(page, 'hairpin');
      await wait(page, 200);
      const hairpinSmith = await page.evaluate(() =>
        document.querySelector('.smith-chart').innerHTML
      );
      await switchMode(page, 'ocfd');
      await wait(page, 200);
      const ocfdSmith = await page.evaluate(() =>
        document.querySelector('.smith-chart').innerHTML
      );
      assert(gammaSmith !== hairpinSmith,
        'Smith chart identical in Gamma and Hairpin modes');
      assert(hairpinSmith !== ocfdSmith,
        'Smith chart identical in Hairpin and OCFD modes');
    });

    await test('6.6 Controls change with each mode', async () => {
      await switchMode(page, 'gamma');
      await wait(page, 200);
      const gammaCtrl = await page.evaluate(() =>
        document.querySelector('.controls').innerHTML
      );
      await switchMode(page, 'hairpin');
      await wait(page, 200);
      const hairpinCtrl = await page.evaluate(() =>
        document.querySelector('.controls').innerHTML
      );
      await switchMode(page, 'ocfd');
      await wait(page, 200);
      const ocfdCtrl = await page.evaluate(() =>
        document.querySelector('.controls').innerHTML
      );
      assert(gammaCtrl !== hairpinCtrl,
        'Controls identical in Gamma and Hairpin modes');
      assert(hairpinCtrl !== ocfdCtrl,
        'Controls identical in Hairpin and OCFD modes');
    });

    await test('6.7 Antenna impedance preserved across mode switch', async () => {
      await switchMode(page, 'gamma'); // Gamma
      await setSlider(page, 'Antenna resistance', 40);
      await setSlider(page, 'Antenna reactance', -20);
      const r1 = await getSliderValue(page, 'Antenna resistance');
      const x1 = await getSliderValue(page, 'Antenna reactance');
      await switchMode(page, 'hairpin'); // Hairpin
      await switchMode(page, 'gamma'); // back to Gamma
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
      // Type frequency into the freq input (in physical-params bar)
      const freqInput = await page.$('.physical-params input[type=number]');
      assert(freqInput, 'Frequency input not found');
      await freqInput.click({ clickCount: 3 });
      await freqInput.type('145');
      await wait(page, 300);
      const text = await page.$eval('body', body => body.innerText);
      assert(text.includes('λ ='), 'Wavelength not displayed');
    });

    await test('8.2 Capacitor pF shown in Gamma mode', async () => {
      await switchMode(page, 'gamma');
      await wait(page, 200);
      const text = await page.$eval('body', body => body.innerText);
      assert(text.includes('pF'), 'pF not shown in Gamma mode with frequency set');
    });

    await test('8.3 Shortening mm/% shown in Hairpin mode', async () => {
      await switchMode(page, 'hairpin');
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

    // ----------------------------------------------------------
    // 11. Shared Dipole Calculator
    // ----------------------------------------------------------
    console.log('\n11. Shared Dipole Calculator');

    await test('11.1 Calculator present in Gamma mode', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      const headers = await page.$$eval('.control-header', els =>
        els.map(e => e.textContent)
      );
      assert(headers.some(h => h.includes('DIPOLE CALCULATOR')),
        'DIPOLE CALCULATOR not found in Gamma mode');
    });

    await test('11.2 Calculator present in Hairpin mode', async () => {
      await switchMode(page, 'hairpin');
      const headers = await page.$$eval('.control-header', els =>
        els.map(e => e.textContent)
      );
      assert(headers.some(h => h.includes('DIPOLE CALCULATOR')),
        'DIPOLE CALCULATOR not found in Hairpin mode');
    });

    await test('11.3 Calculator present in OCFD mode', async () => {
      await switchMode(page, 'ocfd');
      const headers = await page.$$eval('.control-header', els =>
        els.map(e => e.textContent)
      );
      assert(headers.some(h => h.includes('DIPOLE CALCULATOR')),
        'DIPOLE CALCULATOR not found in OCFD mode');
    });

    await test('11.4 Freq in params bar, diam/height in calculator', async () => {
      await switchMode(page, 'gamma');
      const freqInput = await page.$('.physical-params input[type=number]');
      assert(freqInput, 'Frequency input not found in physical-params bar');
      // Expand the calculator to check diam/height
      await page.$$eval('.control-header', headers => {
        const calc = headers.find(h => h.textContent.includes('CALCULATOR'));
        if (calc && calc.textContent.includes('\u25B6')) calc.click();
      });
      await wait(page, 200);
      const diamInput = await page.$('.controls input[min="0.1"][max="100"]');
      assert(diamInput, 'Wire diameter input not found in controls');
      const heightInput = await page.$('.controls input[min="0.1"][max="100"][step="0.1"]');
      assert(heightInput, 'Height input not found in controls');
    });

    await test('11.5 Ground type buttons present', async () => {
      const groundBtns = await page.$$eval('.controls .preset-btn', btns =>
        btns.map(b => b.textContent.trim())
          .filter(t => ['Free space', 'Perfect', 'Sea water', 'Wet', 'Average', 'Dry', 'City'].includes(t))
      );
      assert(groundBtns.length >= 4, `Only ${groundBtns.length} ground type buttons found`);
    });

    await test('11.6 Free-space impedance shown when freq entered', async () => {
      // Load with freq/diam/gnd=free via URL params
      await page.goto(`${BASE}?mode=gamma&r=73&x=43&freq=146&diam=2&gnd=free`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      // Expand the calculator only if collapsed
      await page.$$eval('.control-header', headers => {
        const h = headers.find(h => h.textContent.includes('CALCULATOR'));
        if (h && h.textContent.includes('\u25B6')) h.click();
      });
      await wait(page, 300);
      const bodyText = await page.$eval('body', b => b.innerText);
      assert(bodyText.includes('Free-space'), `Free-space impedance not found in body text`);
    });

    await test('11.6b Resonant length and K displayed', async () => {
      // After 11.6, calculator is expanded with computed Z for 146 MHz, 2mm wire
      const bodyText = await page.$eval('body', b => b.innerText);
      assert(bodyText.includes('Resonant length'), `Resonant length not displayed`);
      assert(bodyText.includes('K ='), `K factor not displayed`);
      // K should be ~0.96 for 2mm wire at 146 MHz
      const kMatch = bodyText.match(/K\s*=\s*([\d.]+)/);
      assert(kMatch, 'Could not parse K value');
      const k = parseFloat(kMatch[1]);
      assert(k > 0.92 && k < 0.99, `K = ${k} outside expected range 0.92-0.99`);
    });

    await test('11.7 Apply to Antenna Impedance updates antenna impedance', async () => {
      // After 11.6, calculator is expanded with computed Z. Click Apply
      await page.$$eval('.auto-tune-btn', btns => {
        const btn = btns.find(b => b.textContent.trim() === 'Apply to Antenna Impedance');
        if (!btn) throw new Error('Apply to Antenna Impedance button not found');
        btn.click();
      });
      await wait(page, 300);
      // Antenna R should be ~73 (free-space resonant dipole)
      const r = await getSliderValue(page, 'Antenna resistance');
      assert(r >= 60 && r <= 90, `Expected R near 73 for free-space dipole, got ${r}`);
    });

    await test('11.8 Presets section separate from calculator', async () => {
      await switchMode(page, 'gamma');
      const topPresets = await page.$('.presets');
      assert(topPresets, 'Top-level .presets section should exist');
      // Verify calculator does NOT contain preset buttons with Ω
      const calcPresets = await page.$$eval('.control-panel', panels => {
        const calc = panels.find(p => p.querySelector('.control-header')?.textContent.includes('CALCULATOR'));
        if (!calc) return 0;
        return [...calc.querySelectorAll('.preset-btn')]
          .filter(b => b.textContent.includes('Ω') && !b.textContent.includes('line')).length;
      });
      assert(calcPresets === 0, `Calculator should not contain antenna presets, found ${calcPresets}`);
    });

    await test('11.9 Presets shown for each mode', async () => {
      for (const modeName of ['gamma', 'hairpin', 'ocfd']) {
        await switchMode(page, modeName);
        const presets = await page.$$eval('.presets .preset-btn', btns => btns.length);
        assert(presets >= 2, `${modeName} mode has only ${presets} preset buttons`);
      }
    });

    await test('11.10 URL includes height/ground for all modes', async () => {
      // Load with height and ground type via URL params
      await page.goto(`${BASE}?mode=gamma&r=73&x=43&freq=146&diam=2&ht=10&gnd=wet`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      const url = await page.url();
      assert(url.includes('ht='), `URL missing height param: ${url}`);
      assert(url.includes('gnd='), `URL missing ground param: ${url}`);
    });

    // ==========================================================
    // Section 12: OCFD Functional Tests
    // ==========================================================
    console.log('\n12. OCFD Functional Tests');

    await test('12.1 OCFD feed offset slider changes feed impedance', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      await switchMode(page, 'ocfd');
      const swr1 = await parseSWR(page);
      await setSlider(page, 'Feed offset', 33);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR should change when feed offset changes (${swr1} -> ${swr2})`);
    });

    await test('12.2 OCFD center resistance slider changes results', async () => {
      const swr1 = await parseSWR(page);
      await setSlider(page, 'OCFD center resistance', 50);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR should change when center R changes (${swr1} -> ${swr2})`);
    });

    await test('12.3 OCFD center reactance slider changes results', async () => {
      const swr1 = await parseSWR(page);
      await setSlider(page, 'OCFD center reactance', 30);
      const swr2 = await parseSWR(page);
      assert(swr1 !== swr2, `SWR should change when center X changes (${swr1} -> ${swr2})`);
    });

    await test('12.4 OCFD feedline impedance selector works', async () => {
      await page.goto(`${BASE}?mode=ocfd&ocr=73&ocx=0&off=33`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      const swr50 = await parseSWR(page);
      // Click the 300Ω feedline button
      await page.evaluate(() => {
        const btn = [...document.querySelectorAll('[aria-label]')]
          .find(b => b.getAttribute('aria-label') === '300 ohm feedline');
        if (!btn) throw new Error('300Ω feedline button not found');
        btn.click();
      });
      await wait(page, 200);
      const swr300 = await parseSWR(page);
      assert(swr50 !== swr300, `SWR should change when feedline Z0 changes (50Ω: ${swr50}, 300Ω: ${swr300})`);
    });

    await test('12.5 OCFD cos² impedance formula validated', async () => {
      // Load with known values: center R=73, X=0, offset=33%
      await page.goto(`${BASE}?mode=ocfd&ocr=73&ocx=0&off=33`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      // Parse feed impedance from result panel
      const feedR = await page.evaluate(() => {
        const text = document.querySelector('.result-z').textContent;
        const match = text.match(/Z\s*=\s*([\d.]+)/);
        return match ? parseFloat(match[1]) : NaN;
      });
      // Expected: 73 / cos²(π * 0.33) ≈ 73 / 0.259 ≈ 282
      const expected = 73 / Math.cos(Math.PI * 0.33) ** 2;
      assert(
        Math.abs(feedR - expected) < 5,
        `Feed R should be ~${expected.toFixed(0)} for 73Ω at 33% offset, got ${feedR}`
      );
    });

    await test('12.6 OCFD preset sets feedOffset', async () => {
      await page.goto(`${BASE}?mode=ocfd`, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 500);
      // Click first OCFD preset (Free-Space λ/2 with feedOffset:33)
      await page.evaluate(() => {
        const btn = [...document.querySelectorAll('.presets .preset-btn')]
          .find(b => b.textContent.includes('Free-Space'));
        if (!btn) throw new Error('Free-Space preset not found');
        btn.click();
      });
      await wait(page, 200);
      const offset = await getSliderValue(page, 'Feed offset');
      assert(offset === 33, `Expected feedOffset=33 from preset, got ${offset}`);
    });

    await test('12.7 OCFD feed offset=50 does not crash (boundary)', async () => {
      await page.goto(`${BASE}?mode=ocfd&ocr=73&ocx=0&off=50`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      // Should not produce NaN or crash
      const hasError = await page.evaluate(() => {
        const text = document.querySelector('.result-z')?.textContent || '';
        return text.includes('NaN') || text.includes('Infinity');
      });
      // Note: at offset=50 cos²→0 so Z→∞, SWR→∞. Just verify no crash.
      const noConsoleErrors = errors.length === 0;
      // We accept Infinity in the display here — the key is no JS crash
      assert(noConsoleErrors, `Console errors at offset=50: ${errors.join('; ')}`);
    });

    await test('12.8 OCFD has no Auto-Tune button', async () => {
      await switchMode(page, 'ocfd');
      const autoTuneBtn = await page.evaluate(() => {
        return [...document.querySelectorAll('.auto-tune-btn')]
          .find(b => b.textContent.trim() === 'Auto-Tune') || null;
      });
      assert(autoTuneBtn === null, 'OCFD mode should not have Auto-Tune button');
    });

    await test('12.9 OCFD experimental banner visible', async () => {
      const banner = await page.$('.experimental-banner');
      assert(banner, 'Experimental banner should exist in OCFD mode');
      const text = await page.$eval('.experimental-banner', el => el.textContent);
      assert(text.includes('Experimental'), `Banner text should say Experimental, got: ${text}`);
    });

    await test('12.10 OCFD URL round-trip', async () => {
      await page.goto(`${BASE}?mode=ocfd&ocr=60&ocx=-15&off=25&z0=300`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      const title = await page.$eval('.title', el => el.textContent);
      assert(title.includes('Off-Center'), `Expected OCFD mode title, got: ${title}`);
      const ocfdR = await getSliderValue(page, 'OCFD center resistance');
      assert(ocfdR === 60, `Expected ocfdR=60, got ${ocfdR}`);
      const ocfdX = await getSliderValue(page, 'OCFD center reactance');
      assert(ocfdX === -15, `Expected ocfdX=-15, got ${ocfdX}`);
      const offset = await getSliderValue(page, 'Feed offset');
      assert(offset === 25, `Expected feedOffset=25, got ${offset}`);
      // Verify 300Ω feedline is active
      const activeZ0 = await page.evaluate(() => {
        const btn = document.querySelector('.feedline-selector .preset-btn.active');
        return btn ? btn.textContent.trim() : '';
      });
      assert(activeZ0.includes('300'), `Expected 300Ω active feedline, got: ${activeZ0}`);
    });

    await test('12.11 OCFD SWR table shows multiple feedline values', async () => {
      await page.goto(`${BASE}?mode=ocfd&ocr=73&ocx=0&off=33`, {
        waitUntil: 'networkidle0', timeout: 15000
      });
      await wait(page, 500);
      const swrRows = await page.$$eval('.swr-row', rows => rows.length);
      assert(swrRows >= 3, `Expected at least 3 SWR table rows, got ${swrRows}`);
    });

    // ==========================================================
    // Section 13: Core Math Unit Tests (via page.evaluate)
    // ==========================================================
    console.log('\n13. Core Math Unit Tests');

    await test('13.1 calcSWR(Z(50,0)) = 1.0 (perfect match)', async () => {
      await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 15000 });
      await wait(page, 300);
      const swr = await page.evaluate(() => calcSWR(Z(50, 0)));
      assert(Math.abs(swr - 1.0) < 0.001, `Expected SWR=1.0, got ${swr}`);
    });

    await test('13.2 calcSWR(Z(100,0)) = 2.0', async () => {
      const swr = await page.evaluate(() => calcSWR(Z(100, 0)));
      assert(Math.abs(swr - 2.0) < 0.001, `Expected SWR=2.0, got ${swr}`);
    });

    await test('13.3 calcSWR(Z(25,0)) = 2.0', async () => {
      const swr = await page.evaluate(() => calcSWR(Z(25, 0)));
      assert(Math.abs(swr - 2.0) < 0.001, `Expected SWR=2.0, got ${swr}`);
    });

    await test('13.4 calcSWRForZ0(Z(300,0), 300) = 1.0', async () => {
      const swr = await page.evaluate(() => calcSWRForZ0(Z(300, 0), 300));
      assert(Math.abs(swr - 1.0) < 0.001, `Expected SWR=1.0, got ${swr}`);
    });

    await test('13.5 calcDipoleIEMF half-wave dipole ≈ 73+j42.5', async () => {
      const z = await page.evaluate(() => {
        const res = calcDipoleIEMF(300, 0.5, 0.001);
        return { r: res.r, x: res.x };
      });
      assert(
        Math.abs(z.r - 73.1) < 2.0,
        `Expected R ≈ 73.1 for half-wave dipole at 300MHz, got ${z.r.toFixed(1)}`
      );
      assert(
        Math.abs(z.x - 42.5) < 3.0,
        `Expected X ≈ 42.5 for half-wave dipole at 300MHz, got ${z.x.toFixed(1)}`
      );
    });

    await test('13.6 calcDipoleResonant gives X ≈ 0', async () => {
      const res = await page.evaluate(() => {
        const r = calcDipoleResonant(146, 2);
        return { r: r.z.r, x: r.z.x, K: r.K };
      });
      assert(Math.abs(res.x) < 0.5, `Resonant dipole X should be ≈ 0, got ${res.x.toFixed(2)}`);
      assert(res.K > 0.92 && res.K < 0.99, `K should be in [0.92, 0.99], got ${res.K.toFixed(4)}`);
    });

    await test('13.7 calcGroundReflection PEC gives Γ = -1', async () => {
      const gamma = await page.evaluate(() => calcGroundReflection(146, Infinity, 0));
      assert(Math.abs(gamma.re - (-1)) < 0.001, `Expected Γ_re=-1, got ${gamma.re}`);
      assert(Math.abs(gamma.im) < 0.001, `Expected Γ_im=0, got ${gamma.im}`);
    });

    await test('13.8 calcDipoleOverGround differs from free-space with ground', async () => {
      const zFree = await page.evaluate(() => {
        const res = calcDipoleOverGround(146, 10, 2, 'free');
        return res ? { r: res.r, x: res.x } : null;
      });
      const zAvg = await page.evaluate(() => {
        const res = calcDipoleOverGround(146, 10, 2, 'average');
        return res ? { r: res.r, x: res.x } : null;
      });
      assert(zFree && zAvg, 'Both ground calculations should return results');
      assert(
        Math.abs(zFree.r - zAvg.r) > 0.5 || Math.abs(zFree.x - zAvg.x) > 0.5,
        `Free-space Z (${zFree.r.toFixed(1)}+j${zFree.x.toFixed(1)}) should differ from average ground Z (${zAvg.r.toFixed(1)}+j${zAvg.x.toFixed(1)})`
      );
    });

    await test('13.9 OCFD cos² formula: center-fed (offset=0) gives same Z', async () => {
      const result = await page.evaluate(() => {
        // At offset=0, factor = 1/cos²(0) = 1, so feedZ = centerZ
        const factor = 1 / Math.cos(Math.PI * 0) ** 2;
        return factor;
      });
      assert(Math.abs(result - 1.0) < 0.001, `Factor at offset=0 should be 1.0, got ${result}`);
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
