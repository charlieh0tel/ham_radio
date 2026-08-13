// Tests for the DOM-free half of random-wire.html.
//
// Run with `npm test` in docs/tools.  The module under test is extracted from
// the page itself, so these exercise the shipped code rather than a copy.

import test from 'node:test';
import assert from 'node:assert/strict';

import * as m from './.check/model.mjs';

const close = (actual, expected, tolerance, what) =>
  assert.ok(Math.abs(actual - expected) <= tolerance,
    `${what}: got ${actual}, expected ${expected} +/- ${tolerance}`);

test('half wave reproduces the 468 / f(MHz) rule at vf 0.95', () => {
  for (const mhz of [3.75, 7.15, 14.175, 28.85]) {
    const feet = m.halfWaveM(mhz * 1e6, 0.95) * m.FT_PER_M;
    close(feet, 468 / mhz, 0.5, `468/f at ${mhz} MHz`);
  }
});

test('feet per metre is the international foot', () => {
  close(m.FT_PER_M, 1 / 0.3048, 1e-12, 'FT_PER_M');
});

test('display units convert against their definitions', () => {
  // Against the definition of the international foot, not against itself:
  // a round trip through a scale factor cannot fail.
  close(m.toDisplay(0.3048, 'ft'), 1, 1e-12, '0.3048 m is one foot');
  close(m.toDisplay(1, 'm'), 1, 1e-12, 'metres are the internal unit');
  close(m.fromDisplay(100, 'ft'), 30.48, 1e-12, '100 ft is 30.48 m');
});

test('a matched load is 1:1 through any transformer', () => {
  for (const ratio of m.UNUN_RATIOS) {
    const swr = m.swrAtRadio({ re: m.Z_SYSTEM_OHMS * ratio, im: 0 }, ratio);
    close(swr, 1, 1e-9, `${ratio}:1 into ${m.Z_SYSTEM_OHMS * ratio} ohms`);
  }
});

test('SWR is symmetric in impedance ratio', () => {
  const high = m.swrAtRadio({ re: m.Z_SYSTEM_OHMS * 4, im: 0 }, 1);
  const low = m.swrAtRadio({ re: m.Z_SYSTEM_OHMS / 4, im: 0 }, 1);
  close(high, low, 1e-9, '4x above and below 50 ohms');
  close(high, 4, 1e-9, 'a 4x mismatch is 4:1');
});

test('coefficient table is well formed', () => {
  // Generated into the page, so a short or misaligned row would interpolate
  // silently against the wrong node.  Stored sparsely: the two antenna-line
  // coefficients are one row along h/lambda, the three return-line ones a
  // row per node pair, because only they vary with counterpoise height.
  const ONE_D = ['alphaA', 'kA'];
  const TWO_D = ['alphaR', 'vfR', 'kR'];
  for (const [geometry, soils] of Object.entries(m.MODEL_COEFFS)) {
    assert.ok(geometry in m.GEOMETRIES, `${geometry} is a known geometry`);
    for (const soil of Object.keys(m.SOILS)) {
      assert.ok(soil in soils, `${geometry}.${soil} has coefficients`);
    }
    for (const [soil, coeffs] of Object.entries(soils)) {
      assert.ok(soil in m.SOILS, `${soil} is a known soil`);
      for (const name of ONE_D) {
        const values = coeffs[name];
        assert.equal(values.length, m.MODEL_H_NODES.length,
          `${geometry}.${soil}.${name} has one value per height node`);
        assert.ok(values.every(Number.isFinite),
          `${geometry}.${soil}.${name} is all finite`);
      }
      for (const name of TWO_D) {
        const rows = coeffs[name];
        assert.equal(rows.length, m.MODEL_H_NODES.length,
          `${geometry}.${soil}.${name} has one row per height node`);
        for (const row of rows) {
          assert.equal(row.length, m.MODEL_Z_NODES.length,
            `${geometry}.${soil}.${name} has one column per counterpoise node`);
          assert.ok(row.every(Number.isFinite),
            `${geometry}.${soil}.${name} is all finite`);
        }
      }
    }
  }
  for (const geometry of Object.keys(m.GEOMETRIES)) {
    assert.ok(geometry in m.MODEL_COEFFS, `${geometry} has coefficients`);
  }
  for (const nodes of [m.MODEL_H_NODES, m.MODEL_Z_NODES]) {
    assert.ok(nodes.every((v, i) => i === 0 || v > nodes[i - 1]),
      'nodes ascend, as the interpolation assumes');
  }
});

test('coefficients interpolate between nodes and clamp outside them', () => {
  const values = m.MODEL_H_NODES.map((_, i) => i);
  const last = m.MODEL_H_NODES.length - 1;
  close(m.interpCoeff(values, m.MODEL_H_NODES[0] / 10), 0, 1e-12, 'below the range');
  close(m.interpCoeff(values, m.MODEL_H_NODES[last] * 10), last, 1e-12,
    'above the range');
  for (let i = 0; i <= last; i++) {
    close(m.interpCoeff(values, m.MODEL_H_NODES[i]), i, 1e-9, `on node ${i}`);
  }
  // Interpolation is linear in log10, so the geometric midpoint is the
  // arithmetic midpoint of the values either side.
  const mid = Math.sqrt(m.MODEL_H_NODES[0] * m.MODEL_H_NODES[1]);
  close(m.interpCoeff(values, mid), 0.5, 1e-9, 'geometric midpoint');
});

test('feedpoint impedance peaks where the model puts its half wave', () => {
  // The regression behind the displayVf bug: the impedance model runs its
  // antenna line at MODEL_VF_A, so its peaks sit there and not at the
  // classical 0.95.  Drawing half waves at the wrong one put the table 5
  // percent away from the curve.
  const site = { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' };
  const freqHz = 14.175e6;
  const expected = m.halfWaveM(freqHz, m.MODEL_VF_A);
  let bestLen = 0;
  let bestMag = -Infinity;
  for (let lenM = expected * 0.8; lenM <= expected * 1.2; lenM += 0.005) {
    const z = m.endFedZin(lenM, freqHz, site, m.WIRE_RADIUS_M);
    const mag = Math.hypot(z.re, z.im);
    if (mag > bestMag) { bestMag = mag; bestLen = lenM; }
  }
  close(bestLen / expected, 1, 0.03, 'peak sits within 3 percent of lambda/2');
  const classical = m.halfWaveM(freqHz, m.DEFAULT_VELOCITY_FACTOR);
  assert.ok(Math.abs(bestLen - classical) > Math.abs(bestLen - expected),
    'peak is nearer the model half wave than the classical one');
  assert.ok(bestMag > 1000, 'a half wave is a high-impedance point');
});

test('a quarter wave is not a high-impedance point', () => {
  const site = { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' };
  const freqHz = 14.175e6;
  const quarter = m.halfWaveM(freqHz, m.MODEL_VF_A) / 2;
  const z = m.endFedZin(quarter, freqHz, site, m.WIRE_RADIUS_M);
  assert.ok(Math.hypot(z.re, z.im) < 1000, 'quarter wave stays below a kilohm');
});

test('raising the wire changes the answer', () => {
  // Height was unmodelled before the fit; a model that ignores it would
  // return the same impedance twice.
  const freqHz = 7.15e6;
  const lenM = 21.6;
  const low = m.endFedZin(lenM, freqHz,
    { geometry: 'flatTop', heightM: 3, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' }, m.WIRE_RADIUS_M);
  const high = m.endFedZin(lenM, freqHz,
    { geometry: 'flatTop', heightM: 20, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' }, m.WIRE_RADIUS_M);
  assert.ok(Math.abs(Math.hypot(low.re, low.im) - Math.hypot(high.re, high.im)) > 1,
    'height moves the feedpoint');
});

test('suggested lengths are ordered, distinct and long enough', () => {
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const out = m.solveImpedance('us', [80, 40, 20, 15, 10], 'full', site,
    m.WIRE_RADIUS_M, 9, 60, 'ft');
  assert.ok(out.suggestions.length > 0, 'something is suggested');
  for (let i = 1; i < out.suggestions.length; i++) {
    assert.ok(out.suggestions[i].swr >= out.suggestions[i - 1].swr,
      'suggestions are best first');
  }
  for (const s of out.suggestions) {
    assert.ok(s.lenM >= out.shortLimit, 'no suggestion below the short limit');
    assert.ok(Number.isFinite(s.swr) && s.swr >= 1, 'SWR is a real ratio');
  }
});

test('no bands selected yields no suggestions rather than throwing', () => {
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const out = m.solveImpedance('us', [], 'full', site, m.WIRE_RADIUS_M, 9, 30,
    'ft');
  assert.deepEqual(out.suggestions, []);
  assert.deepEqual(out.curve, []);
});

test('the classical rule keeps its stated clearance', () => {
  const marginPct = 8;
  const out = m.solve('us', [40], 'full', 0.95, marginPct, 60, 'ft');
  for (const span of out.suggestions) {
    for (const zone of out.merged) {
      const inside = span.pick > zone.lo && span.pick < zone.hi;
      assert.ok(!inside, `pick ${span.pick} avoids ${zone.lo}-${zone.hi}`);
    }
  }
});

// ---------------------------------------------------------------------------
// Band plans and segments
// ---------------------------------------------------------------------------

test('every region has bands, and every band a sane edge pair', () => {
  for (const region of Object.keys(m.REGIONS)) {
    const bands = m.bandsIn(region);
    assert.ok(bands.length > 0, `${region} has bands`);
    for (const band of bands) {
      for (const segment of Object.keys(m.SEGMENTS)) {
        const [lo, hi] = m.bandEdgesHz(band, segment);
        assert.ok(lo > 0 && hi > lo, `${region} ${band.m}m ${segment}: ${lo}-${hi}`);
        assert.ok(hi / lo < 1.2, `${region} ${band.m}m ${segment} spans < 20 percent`);
      }
    }
  }
});

test('band metres and frequency agree', () => {
  // A band labelled 40 m should sit near 300/40 = 7.5 MHz.  Catches a row
  // typed into the wrong place in the band table.
  for (const region of Object.keys(m.REGIONS)) {
    for (const band of m.bandsIn(region)) {
      const [lo, hi] = m.bandEdgesHz(band, 'full');
      const centreM = m.C_SPEED / ((lo + hi) / 2);
      close(centreM / band.m, 1, 0.15, `${region} ${band.m}m centre wavelength`);
    }
  }
});

test('a sub-band lies inside the full band', () => {
  for (const region of Object.keys(m.REGIONS)) {
    for (const band of m.bandsIn(region)) {
      const [fullLo, fullHi] = m.bandEdgesHz(band, 'full');
      for (const segment of Object.keys(m.SEGMENTS)) {
        const [lo, hi] = m.bandEdgesHz(band, segment);
        assert.ok(lo >= fullLo && hi <= fullHi,
          `${region} ${band.m}m ${segment} within the full band`);
      }
    }
  }
});

// ---------------------------------------------------------------------------
// Length math
// ---------------------------------------------------------------------------

test('half wave scales inversely with frequency and with velocity factor', () => {
  close(m.halfWaveM(7e6, 1) / m.halfWaveM(14e6, 1), 2, 1e-9, 'halving frequency');
  close(m.halfWaveM(7e6, 0.5) / m.halfWaveM(7e6, 1), 0.5, 1e-9, 'halving vf');
});

test('a resonance interval brackets the half wave it is built from', () => {
  const band = m.bandsIn('us').find(b => b.m === 40);
  const [lo, hi] = m.bandEdgesHz(band, 'full');
  const interval = m.resonanceInterval(band, 'full', 0.95, 0.08, 1);
  assert.ok(interval.lo < m.halfWaveM(hi, 0.95), 'reaches below the shortest');
  assert.ok(interval.hi > m.halfWaveM(lo, 0.95), 'reaches above the longest');
  assert.ok(interval.lo < interval.hi, 'ordered');
});

test('a wider margin never narrows a keep-out zone', () => {
  const band = m.bandsIn('us').find(b => b.m === 20);
  let previous = null;
  for (const margin of [0, 0.02, 0.05, 0.1, 0.15]) {
    const interval = m.resonanceInterval(band, 'full', 0.95, margin, 1);
    if (previous) {
      assert.ok(interval.lo <= previous.lo, 'low edge moves down or holds');
      assert.ok(interval.hi >= previous.hi, 'high edge moves up or holds');
    }
    previous = interval;
  }
});

test('each avoid zone delivers the clearance it promises', () => {
  // avoidIntervals returns one zone per band per multiple; overlap between
  // bands is expected here and resolved by solve().
  const bands = m.bandsIn('us').filter(b => [40, 20, 15].includes(b.m));
  // The property worth asserting is the clearance itself: each zone must
  // reach at least marginPct of a half wave either side of the resonance it
  // guards, which is the whole claim the classical mode makes.
  const marginPct = 8;
  for (const band of bands) {
    const [loHz, hiHz] = m.bandEdgesHz(band, 'full');
    const shortest = m.halfWaveM(hiHz, 0.95);
    const longest = m.halfWaveM(loHz, 0.95);
    for (let n = 1; n * shortest <= 60; n++) {
      const zone = m.resonanceInterval(band, 'full', 0.95, marginPct / 100, n);
      assert.ok(zone.lo <= (n - marginPct / 100) * shortest + 1e-9,
        `${band.label} n=${n}: low edge clears by the stated margin`);
      assert.ok(zone.hi >= (n + marginPct / 100) * longest - 1e-9,
        `${band.label} n=${n}: high edge clears by the stated margin`);
    }
  }
});

test('solve merges the avoid zones into disjoint ones', () => {
  const out = m.solve('us', [40, 20, 15], 'full', 0.95, 8, 60, 'ft');
  for (let i = 1; i < out.merged.length; i++) {
    assert.ok(out.merged[i].lo > out.merged[i - 1].hi,
      'merged zones are disjoint and ascending');
  }
  for (const zone of out.merged) {
    assert.ok(zone.lo < zone.hi, 'merged zone is ordered');
  }
});

test('usable spans clear every avoid zone', () => {
  const out = m.solve('us', [40, 20], 'full', 0.95, 8, 60, 'ft');
  for (const span of out.usable) {
    for (const zone of out.merged) {
      const overlaps = span.lo < zone.hi && zone.lo < span.hi;
      assert.ok(!overlaps, `usable ${span.lo}-${span.hi} clears ${zone.lo}-${zone.hi}`);
    }
  }
});

test('the short limit is a quarter wave at the lowest band', () => {
  const bands = m.bandsIn('us').filter(b => [80, 40, 20].includes(b.m));
  const limit = m.tooShortM(bands, 'full', 0.95);
  const lowest = Math.min(...bands.map(b => m.bandEdgesHz(b, 'full')[0]));
  close(limit, m.halfWaveM(lowest, 0.95) / 2, 1e-9, 'quarter wave on 80 m');
});

// ---------------------------------------------------------------------------
// Impedance model
// ---------------------------------------------------------------------------

test('Schelkunoff Z0 rises with length and falls with radius', () => {
  assert.ok(m.wireZ0(40, 8.14e-4) > m.wireZ0(20, 8.14e-4), 'longer is higher');
  assert.ok(m.wireZ0(20, 1.6e-3) < m.wireZ0(20, 8.14e-4), 'fatter is lower');
  // 60 (ln(2l/a) - 1) at l = 20 m, a = 0.814 mm.
  close(m.wireZ0(20, 8.14e-4), 60 * (Math.log(2 * 20 / 8.14e-4) - 1), 1e-9,
    'matches the closed form');
});

test('feedpoint impedance is finite and positive-real everywhere sampled', () => {
  const site = { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' };
  for (const mhz of [1.9, 3.75, 7.15, 14.175, 21.225, 28.85]) {
    for (let lenM = 2; lenM <= 60; lenM += 0.5) {
      const z = m.endFedZin(lenM, mhz * 1e6, site, m.WIRE_RADIUS_M);
      assert.ok(Number.isFinite(z.re) && Number.isFinite(z.im),
        `finite at ${lenM} m, ${mhz} MHz`);
      assert.ok(z.re > 0, `resistive part positive at ${lenM} m, ${mhz} MHz`);
    }
  }
});

test('every soil produces a usable model', () => {
  const freqHz = 14.175e6;
  for (const soil of Object.keys(m.SOILS)) {
    const z = m.endFedZin(20, freqHz, { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil },
      m.WIRE_RADIUS_M);
    assert.ok(Number.isFinite(z.re) && z.re > 0, `${soil} gives a real impedance`);
  }
});

test('SWR matches the closed form either side of a match', () => {
  // Values chosen against the closed form rather than against the code: a
  // load n times the system impedance is n:1, either side of the match.
  for (const [ohms, ratio, want] of [[450, 9, 1], [1800, 9, 4], [112.5, 9, 4],
                                     [2450, 49, 1], [50, 1, 1], [200, 1, 4]]) {
    close(m.swrAtRadio({ re: ohms, im: 0 }, ratio), want, 1e-9,
      `${ohms} ohms through ${ratio}:1`);
  }
  const matched = m.swrAtRadio({ re: 450, im: 0 }, 9);
  const reactive = m.swrAtRadio({ re: 450, im: 450 }, 9);
  assert.ok(reactive > matched, 'reactance makes the match worse');
});

test('scoring a length returns a mean bounded by its own worst case', () => {
  const site = { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 7.62, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' };
  const bands = m.bandsIn('us').filter(b => [40, 20, 10].includes(b.m));
  const scored = m.scoreLength(21.6, bands, 'full', site, m.WIRE_RADIUS_M, 9);
  assert.ok(scored !== null, 'a score comes back');
  assert.ok(scored.swr >= 1, 'geometric mean is a ratio');
  assert.ok(bands.some(b => b.m === scored.worst.band.m),
    'the worst band is one that was asked for');
});

test('a longer return path changes the score', () => {
  // Finding 4: the return resonates in its own right.  A model that treated
  // it as a passive ground would return the same number twice.
  const bands = m.bandsIn('us').filter(b => [40, 20].includes(b.m));
  const short = m.scoreLength(21.6, bands, 'full',
    { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 3, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' }, m.WIRE_RADIUS_M, 9);
  const long = m.scoreLength(21.6, bands, 'full',
    { geometry: 'flatTop', heightM: 9.144, balunM: m.DEFAULT_BALUN_M, counterpoiseM: 30, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, soil: 'average' }, m.WIRE_RADIUS_M, 9);
  assert.ok(Math.abs(short.swr - long.swr) > 0.01, 'return length matters');
});

test('the transformer ratio moves the match', () => {
  const z = { re: 450, im: 0 };
  close(m.swrAtRadio(z, 9), 1, 1e-9, '450 ohms through 9:1');
  assert.ok(m.swrAtRadio(z, 1) > 8, '450 ohms direct is a poor match');
  assert.ok(m.swrAtRadio({ re: 2450, im: 0 }, 49) < 1.1, '2450 through 49:1');
});

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

test('lengths format in the unit asked for', () => {
  assert.match(m.fmtLen(30.48, 'ft'), /100/, '30.48 m is 100 ft');
  assert.match(m.fmtLen(30.48, 'm'), /30/, '30.48 m reads as metres');
  assert.match(m.fmtLen(30.48, 'ftin'), /100/, 'ft + in still leads with feet');
});

test('feet and inches never shows twelve inches', () => {
  for (let cm = 0; cm < 400; cm += 1) {
    const text = m.fmtLen(cm / 100, 'ftin');
    const inches = text.match(/([\d.]+)\s*in/);
    if (inches) {
      assert.ok(Number(inches[1]) < 12, `${text} carries into feet`);
    }
  }
});

// ---------------------------------------------------------------------------
// The page against the fit it came from
// ---------------------------------------------------------------------------

test('inlined coefficients match the fitted table they were generated from', async () => {
  // The page must stay self-contained, so its coefficients are inlined rather
  // than imported.  nec/random_wire/coefficients2d.json is the original, and
  // this is what stops the two drifting: regenerate with
  // `uv run coefficients2d.py --write-page` and both move together.
  const { readFile } = await import('node:fs/promises');
  const url = new URL('../../nec/random_wire/coefficients2d.json', import.meta.url);
  const data = JSON.parse(await readFile(url, 'utf8'));

  assert.deepEqual([...m.MODEL_H_NODES], data.h_nodes, 'height nodes agree');
  assert.deepEqual([...m.MODEL_Z_NODES], data.z_nodes, 'counterpoise nodes agree');
  close(m.MODEL_VF_A, data.vf_a, 1e-12, 'antenna velocity factor');

  // The json carries a dense (soil, height, counterpoise, parameter) array;
  // the page stores the two antenna coefficients once, since they do not
  // vary along the counterpoise axis.
  const JS = { alpha_a_lam: 'alphaA', ka: 'kA', alpha_r_lam: 'alphaR',
               vf_r: 'vfR', kr: 'kR' };
  const round = (v) => Math.round(v * 1e4) / 1e4;
  for (const [key, geometry] of [['flat_top', 'flatTop'], ['sloper', 'sloper']]) {
    const table = data[key].table;
    data.soils.forEach((soil, si) => {
      data.params.forEach((param, pi) => {
        const name = JS[param];
        const inlined = m.MODEL_COEFFS[geometry][soil][name];
        if (data.two_d_params.includes(param)) {
          table[si].forEach((row, ni) => {
            assert.deepEqual([...inlined[ni]], row.map((cell) => round(cell[pi])),
              `${geometry}.${soil}.${name} row ${ni} matches the fit`);
          });
          return;
        }
        assert.deepEqual([...inlined],
          table[si].map((row) => round(row[0][pi])),
          `${geometry}.${soil}.${name} matches the fit`);
      });
    });
  }
});

test('the fitted coefficients are physically plausible', () => {
  // Loss cannot be negative, a velocity factor above one is a wave outrunning
  // light, and a Z0 scale far from unity means the line form has stopped
  // describing a wire.  A bad sweep point reaching the fit shows up here.
  for (const [geometry, soils] of Object.entries(m.MODEL_COEFFS)) {
    for (const [soil, coeffs] of Object.entries(soils)) {
      const where = `${geometry}.${soil}`;
      for (const alpha of [...coeffs.alphaA, ...coeffs.alphaR.flat()]) {
        assert.ok(alpha > 0 && alpha < 5, `${where}: alpha ${alpha} in range`);
      }
      for (const vf of coeffs.vfR.flat()) {
        assert.ok(vf > 0.3 && vf <= 1.0001, `${where}: vf_r ${vf} at or below unity`);
      }
      for (const k of [...coeffs.kA, ...coeffs.kR.flat()]) {
        assert.ok(k > 0.2 && k < 2, `${where}: Z0 scale ${k} near unity`);
      }
    }
  }
});

// ---------------------------------------------------------------------------
// The two modes against each other
// ---------------------------------------------------------------------------
//
// The classical keep-out is a proxy: those lengths are bad because the
// feedpoint impedance spikes there.  The impedance mode drops the proxy and
// models the spike.  So the two should agree about where the bad lengths are,
// and where they disagree it should be for a reason that can be named.
//
// The comparison is made at MODEL_VF_A throughout.  The modes ship with
// different velocity factors, which offsets every zone by about 5 percent;
// that difference is a live decision recorded in RANDOM_WIRE_TODO.md, and
// holding it fixed here is what lets these tests speak to anything else.

const AT_MODEL_VF = { region: 'us', segment: 'full', marginPct: 8 };

test('the classical avoid zones bracket the modelled impedance peaks', () => {
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bandM = 20;
  const band = m.bandsIn(AT_MODEL_VF.region).find(b => b.m === bandM);
  const [loHz, hiHz] = m.bandEdgesHz(band, AT_MODEL_VF.segment);
  const midHz = (loHz + hiHz) / 2;

  const zones = m.avoidIntervals([band], AT_MODEL_VF.segment, m.MODEL_VF_A,
    AT_MODEL_VF.marginPct, 60);
  assert.ok(zones.length > 0, 'the rule marks something out');

  // Every peak the model draws should fall inside a zone the rule marks.
  const peaks = [];
  let previous = null;
  let rising = false;
  for (let lenM = 2; lenM <= 60; lenM += 0.02) {
    const z = m.endFedZin(lenM, midHz, site, m.WIRE_RADIUS_M);
    const mag = Math.hypot(z.re, z.im);
    if (previous !== null) {
      if (mag > previous) rising = true;
      else if (rising) { peaks.push(lenM - 0.02); rising = false; }
    }
    previous = mag;
  }
  assert.ok(peaks.length >= 3, `found ${peaks.length} peaks to check`);
  for (const peak of peaks) {
    const covered = zones.some(zone => peak >= zone.lo && peak <= zone.hi);
    assert.ok(covered, `peak at ${peak.toFixed(2)} m falls in an avoid zone`);
  }
});

test('lengths the classical rule rejects score worse than ones it accepts', () => {
  // The two methods are independent: one is arithmetic on wavelength, the
  // other a fitted impedance model.  If the proxy is sound they should rank
  // the same lengths the same way.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bandsM = [40, 20, 15];
  const bands = m.bandsIn(AT_MODEL_VF.region).filter(b => bandsM.includes(b.m));
  const zones = m.avoidIntervals(bands, AT_MODEL_VF.segment, m.MODEL_VF_A,
    AT_MODEL_VF.marginPct, 60);

  const inside = [];
  const outside = [];
  for (let lenM = 8; lenM <= 45; lenM += 0.25) {
    const scored = m.scoreLength(lenM, bands, AT_MODEL_VF.segment, site,
      m.WIRE_RADIUS_M, 9);
    const hit = zones.some(zone => lenM >= zone.lo && lenM <= zone.hi);
    (hit ? inside : outside).push(scored.swr);
  }
  assert.ok(inside.length > 5 && outside.length > 5, 'both sets are populated');

  const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
  assert.ok(median(inside) > median(outside),
    `rejected lengths score worse: ${median(inside).toFixed(2)} ` +
    `against ${median(outside).toFixed(2)}`);
});

test('the two modes recommend lengths that are mutually acceptable', () => {
  // The strongest form: what one method offers, the other should not have
  // ruled out.  Checked on a band set where the classical rule still has room
  // to have an opinion -- see the saturation test below for why that
  // qualifier is needed rather than a way of ducking the comparison.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bandsM = [40, 20];
  const bands = m.bandsIn(AT_MODEL_VF.region).filter(b => bandsM.includes(b.m));
  const zones = m.avoidIntervals(bands, AT_MODEL_VF.segment, m.MODEL_VF_A,
    AT_MODEL_VF.marginPct, 60);

  const impedance = m.solveImpedance(AT_MODEL_VF.region, bandsM,
    AT_MODEL_VF.segment, site, m.WIRE_RADIUS_M, 9, 60, 'ft');
  assert.ok(impedance.suggestions.length > 0, 'the impedance mode offers something');
  for (const pick of impedance.suggestions) {
    const hit = zones.find(zone => pick.lenM >= zone.lo && pick.lenM <= zone.hi);
    assert.ok(hit === undefined,
      `impedance pick ${pick.lenM.toFixed(2)} m is not in a classical avoid zone`);
  }
});

test('the classical rule saturates once enough bands are asked for', () => {
  // Not a failure of either method, but the reason the mutual-acceptability
  // check above is qualified, and an argument for the impedance mode: with
  // four bands at the default margin the keep-out zones cover more than the
  // whole axis, so every length is in one and "avoid resonance" stops being
  // advice.  A continuous cost still ranks them; a binary rule cannot.
  const bands = m.bandsIn('us').filter(b => [40, 20, 15, 10].includes(b.m));
  const zones = m.avoidIntervals(bands, 'full', m.MODEL_VF_A, 8, 60);
  const covered = zones.reduce((sum, z) => sum + (z.hi - z.lo), 0);
  assert.ok(covered > 60, `zones cover ${covered.toFixed(1)} m of a 60 m axis`);

  const solved = m.solve('us', [40, 20, 15, 10], 'full', m.MODEL_VF_A, 8, 60, 'ft');
  const widest = Math.max(...solved.usable.map(u => u.hi - u.lo));
  assert.ok(widest < 5, `widest usable span is only ${widest.toFixed(2)} m`);

  // The impedance mode still returns a ranking over the same input.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const scored = m.solveImpedance('us', [40, 20, 15, 10], 'full', site,
    m.WIRE_RADIUS_M, 9, 60, 'ft');
  assert.ok(scored.suggestions.length > 0,
    'the impedance mode still has an opinion where the rule has none');
});

test('the published lengths are scored rather than omitted', () => {
  // The page shows what it thinks of the standard tables, including where it
  // disagrees.  A user who knows 71 ft will otherwise read its absence from
  // the suggestions as a broken tool.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bands = m.bandsIn('us').filter(b => [80, 40, 20, 15, 10].includes(b.m));
  assert.ok(m.PUBLISHED_FT.includes(71), '71 ft is among the lengths shown');

  const scores = m.PUBLISHED_FT.map(ft => ({
    ft, swr: m.scoreLength(m.fromDisplay(ft, 'ft'), bands, 'full', site,
      m.WIRE_RADIUS_M, 9).swr,
  }));
  for (const { ft, swr } of scores) {
    assert.ok(Number.isFinite(swr) && swr >= 1, `${ft} ft scores a real SWR`);
  }
  // Mostly agreeing with the tables on the average is what makes the
  // disagreements worth reading; if this flips, the model has drifted rather
  // than dissented.  Judged against a fixed 5:1 rather than the default
  // tuner, so that changing which tuner the page opens on does not silently
  // change what this asserts.
  const AGREEMENT_SWR = 5;
  const passing = scores.filter(s => s.swr <= AGREEMENT_SWR).length;
  assert.ok(passing >= scores.length / 2,
    `${passing} of ${scores.length} published lengths pass on the mean`);
});

test('the worst-band gate is what separates the published lengths', () => {
  // The two agree on the average and part company on the worst band, and it
  // is 80 m that does it: a random wire is electrically short there and the
  // match is genuinely hard.  Recorded as a test because the default band set
  // includes 80 m, so this is what a first-time visitor sees.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  // Against a wide-range tuner, not the default: with a rig ATU almost
  // nothing passes either way and the comparison says nothing.
  const passing = (bandsM) => {
    const bands = m.bandsIn('us').filter(b => bandsM.includes(b.m));
    return m.PUBLISHED_FT.filter(ft => m.isGoodScore(
      m.scoreLength(m.fromDisplay(ft, 'ft'), bands, 'full', site,
        m.WIRE_RADIUS_M, 9), 'roller')).length;
  };
  const withEighty = passing([80, 40, 20, 15, 10]);
  const without = passing([40, 20, 15, 10]);
  assert.ok(without > withEighty,
    `dropping 80 m should help: ${withEighty} -> ${without}`);
});

test('every offered band lies inside the fitted frequency range', () => {
  // The impedance mode quotes an accuracy figure that only means anything
  // where the sweep has evidence.  Rather than warning at runtime about bands
  // outside it, the band tables are held inside it here: adding 6 m or 630 m
  // back means extending the sweep first, and this test is what says so.
  for (const region of Object.keys(m.REGIONS)) {
    for (const band of m.bandsIn(region)) {
      for (const segment of Object.keys(m.SEGMENTS)) {
        const [lo, hi] = m.bandEdgesHz(band, segment);
        assert.ok(lo >= m.MODEL_FIT_RANGE_HZ.min,
          `${region} ${band.label} ${segment} starts at ${lo} Hz, below the fit`);
        assert.ok(hi <= m.MODEL_FIT_RANGE_HZ.max,
          `${region} ${band.label} ${segment} ends at ${hi} Hz, above the fit`);
      }
    }
  }
});

test('impedance suggestions are round numbers whose score matches the length', () => {
  // A raw local minimum lands wherever the sample grid falls, so it is an
  // artefact of SCORE_SAMPLES rather than a length to cut wire to.  Each
  // suggestion must round in the display unit and carry the score of the
  // rounded length, not of the sample it came from.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bandsM = [40, 20, 15, 10];
  for (const units of Object.keys(m.UNITS)) {
    const out = m.solveImpedance('us', bandsM, 'full', site, m.WIRE_RADIUS_M,
      9, 60, units);
    assert.ok(out.suggestions.length > 0, `${units}: something is suggested`);
    const seen = new Set();
    for (const pick of out.suggestions) {
      const display = m.toDisplay(pick.lenM, units);
      close(display, Math.round(display * 100) / 100, 1e-9,
        `${units}: ${display} is round in the display unit`);
      assert.ok(!seen.has(pick.lenM), `${units}: no duplicate after rounding`);
      seen.add(pick.lenM);
      const rescored = m.scoreLength(pick.lenM, out.bands, 'full', site,
        m.WIRE_RADIUS_M, 9);
      close(pick.swr, rescored.swr, 1e-9,
        `${units}: the quoted SWR is the rounded length's own`);
    }
  }
});

// ---------------------------------------------------------------------------
// The classical verdict, which had no tests at all
// ---------------------------------------------------------------------------

/** The default site, spelled once. */
const SITE = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
  soil: m.DEFAULT_SOIL };

test('judgeLength calls a length inside an avoid zone bad', () => {
  const bands = m.bandsIn('us').filter(b => b.m === 40);
  const zone = m.resonanceInterval(bands[0], 'full', 0.95, 0.08, 1);
  const middle = (zone.lo + zone.hi) / 2;
  const shortLimit = m.tooShortM(bands, 'full', 0.95);
  const verdict = m.judgeLength(middle, bands, 'full', 0.95, 8, shortLimit);
  assert.ok(verdict !== null, 'a length long enough gets a verdict');
  assert.equal(verdict.ok, false, 'the middle of a keep-out zone is not ok');
  assert.ok(verdict.hit !== null, 'and it names the zone it landed in');
  assert.ok(verdict.hit.lo <= middle && middle <= verdict.hit.hi,
    'the named zone actually contains the length');
});

test('judgeLength calls a length between zones good, and measures clearance', () => {
  const bands = m.bandsIn('us').filter(b => b.m === 40);
  const solved = m.solve('us', [40], 'full', 0.95, 8, 60, 'ft');
  const span = solved.usable.find(u => u.hi - u.lo > 1);
  assert.ok(span !== undefined, 'a usable span exists to test in');
  const middle = (span.lo + span.hi) / 2;
  const shortLimit = m.tooShortM(bands, 'full', 0.95);
  const verdict = m.judgeLength(middle, bands, 'full', 0.95, 8, shortLimit);
  assert.equal(verdict.ok, true, 'the middle of a usable span is ok');
  assert.equal(verdict.hit, null, 'nothing was hit');
  assert.ok(verdict.clearance > 0, 'clearance is positive');
  // The clearance must be the true distance to the nearest zone edge.
  const nearest = Math.min(...solved.merged.map(
    z => Math.min(Math.abs(middle - z.lo), Math.abs(middle - z.hi))));
  close(verdict.clearance, nearest, 1e-6, 'clearance is the real distance');
});

test('judgeLength explains a too-short wire rather than refusing one', () => {
  const bands = m.bandsIn('us').filter(b => b.m === 80);
  const shortLimit = m.tooShortM(bands, 'full', 0.95);
  const verdict = m.judgeLength(shortLimit * 0.5, bands, 'full', 0.95, 8,
    shortLimit);
  assert.ok(verdict !== null, 'a short wire still gets a verdict');
  assert.equal(verdict.ok, false, 'and it is not a good one');
  assert.equal(verdict.hit.kind, 'short',
    'the reason given is the length, not a resonance');
  // Only a nonsensical length gets nothing back.
  assert.equal(m.judgeLength(0, bands, 'full', 0.95, 8, shortLimit), null,
    'zero length has no verdict to give');
  assert.equal(m.judgeLength(-5, bands, 'full', 0.95, 8, shortLimit), null,
    'nor does a negative one');
});

test('a wider margin can only turn a good length bad, never the reverse', () => {
  // The zones only grow with the margin, so a length inside one at 5 percent
  // cannot be outside it at 12.  This is the monotonicity the whole rule
  // rests on, and it is what a sign error in resonanceInterval would break.
  const bands = m.bandsIn('us').filter(b => [40, 20].includes(b.m));
  const shortLimit = m.tooShortM(bands, 'full', 0.95);
  for (let lenM = 10; lenM < 50; lenM += 0.37) {
    let wasBad = false;
    for (const marginPct of [0, 2, 5, 8, 12, 15]) {
      const verdict = m.judgeLength(lenM, bands, 'full', 0.95, marginPct,
        shortLimit);
      if (verdict === null) continue;
      if (wasBad) {
        assert.equal(verdict.ok, false,
          `${lenM.toFixed(2)} m went bad then good again at ${marginPct}%`);
      }
      if (!verdict.ok) wasBad = true;
    }
  }
});

// ---------------------------------------------------------------------------
// Interval algebra and the pickers
// ---------------------------------------------------------------------------

test('mergeIntervals unions overlaps and leaves gaps alone', () => {
  const merged = m.mergeIntervals([
    { lo: 5, hi: 10 }, { lo: 8, hi: 12 }, { lo: 20, hi: 25 }, { lo: 1, hi: 3 },
  ]);
  assert.deepEqual(merged.map(i => [i.lo, i.hi]),
    [[1, 3], [5, 12], [20, 25]], 'sorted, unioned, gaps preserved');
});

test('mergeIntervals joins intervals that only touch', () => {
  const merged = m.mergeIntervals([{ lo: 0, hi: 5 }, { lo: 5, hi: 9 }]);
  assert.equal(merged.length, 1, 'abutting intervals are one');
});

test('usableIntervals is the complement of the merged zones', () => {
  const usable = m.usableIntervals([{ lo: 5, hi: 10 }, { lo: 20, hi: 25 }], 30);
  for (const span of usable) {
    assert.ok(span.lo < span.hi, 'each span is ordered');
    for (const zone of [{ lo: 5, hi: 10 }, { lo: 20, hi: 25 }]) {
      assert.ok(!(span.lo < zone.hi && zone.lo < span.hi),
        `${span.lo}-${span.hi} does not overlap ${zone.lo}-${zone.hi}`);
    }
  }
  // Coverage, which the old test never checked: every point not in a zone
  // has to be in a span.
  for (const probe of [1, 4.9, 12, 19, 26, 29.9]) {
    assert.ok(usable.some(s => probe >= s.lo && probe <= s.hi),
      `${probe} is covered`);
  }
});

test('pickInSpan returns a round number strictly inside the span', () => {
  for (const span of [{ lo: 10, hi: 20 }, { lo: 10.02, hi: 10.06 },
                      { lo: 0.5, hi: 0.51 }]) {
    for (const units of Object.keys(m.UNITS)) {
      const pick = m.pickInSpan(span, units);
      assert.ok(pick > span.lo && pick < span.hi,
        `${units}: ${pick} is inside ${span.lo}-${span.hi}`);
    }
  }
});

test('pickInSpan prefers the roundest number that fits', () => {
  // A wide span should give a whole number of feet, not a fractional one.
  const pick = m.toDisplay(m.pickInSpan({ lo: 10, hi: 20 }, 'ft'), 'ft');
  close(pick, Math.round(pick), 1e-9, 'a wide span picks a whole foot');
});

test('bestFeasibleMargin finds a margin that leaves something', () => {
  // Called only when the asked-for margin empties the axis, so what matters
  // is that what it returns actually works.
  const fallback = m.bestFeasibleMargin('us', [40, 20, 15, 10], 'full', 0.95,
    m.MARGIN_PCT_RANGE.max, 60, 'ft');
  if (fallback === null) return;
  assert.ok(fallback.marginPct >= m.MARGIN_PCT_RANGE.min);
  assert.ok(fallback.marginPct <= m.MARGIN_PCT_RANGE.max);
  const solved = m.solve('us', [40, 20, 15, 10], 'full', 0.95,
    fallback.marginPct, 60, 'ft');
  assert.ok(solved.suggestions.length > 0,
    `the margin it recommends (${fallback.marginPct}%) really does solve`);
});

// ---------------------------------------------------------------------------
// URL round-tripping, which the page promises and could not test
// ---------------------------------------------------------------------------

test('a length written as metres reads back unchanged', () => {
  const params = new URLSearchParams({ [m.URL_KEYS.wireLenM]: '21.336' });
  close(m.readWireLenM(params), 21.336, 1e-9, 'len_m is metres');
});

test('the legacy ?len= is still read as feet', () => {
  // docs/AGENTS.md promises links shared before the SI conversion resolve to
  // the same wire.  Nothing checked it until now.
  const params = new URLSearchParams({ [m.LEGACY_LEN_FT_KEY]: '70' });
  close(m.readWireLenM(params), 70 * 0.3048, 1e-9, '70 ft is 21.336 m');
});

test('the modern key wins when both are present', () => {
  const params = new URLSearchParams({
    [m.URL_KEYS.wireLenM]: '30', [m.LEGACY_LEN_FT_KEY]: '70' });
  close(m.readWireLenM(params), 30, 1e-9, 'len_m takes precedence over len');
});

test('a missing or unparseable length falls back to the default', () => {
  close(m.readWireLenM(new URLSearchParams()), m.DEFAULTS.wireLenM, 1e-9,
    'absent');
  close(m.readWireLenM(new URLSearchParams({ [m.URL_KEYS.wireLenM]: 'x' })),
    m.DEFAULTS.wireLenM, 1e-9, 'unparseable');
});

test('clamp and parseNum hold their ranges', () => {
  close(m.clamp(5, { min: 0, max: 3 }), 3, 1e-9, 'above');
  close(m.clamp(-5, { min: 0, max: 3 }), 0, 1e-9, 'below');
  close(m.parseNum('2.5', 9), 2.5, 1e-9, 'parses');
  close(m.parseNum(null, 9), 9, 1e-9, 'null falls back');
  close(m.parseNum('nonsense', 9), 9, 1e-9, 'garbage falls back');
});

test('isKeyOf keeps a bad URL parameter out of a lookup table', () => {
  assert.equal(m.isKeyOf(m.SOILS, 'average'), true);
  assert.equal(m.isKeyOf(m.SOILS, 'swamp'), false);
  assert.equal(m.isKeyOf(m.SOILS, null), false);
  assert.equal(m.isKeyOf(m.SOILS, 'toString'), false,
    'an inherited property is not a key');
});

test('the tuner preset decides what counts as a good length', () => {
  // The gates are the point of the preset, so a stricter tuner must accept a
  // subset of what a looser one does -- never something different.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bands = m.bandsIn('us').filter(b => m.DEFAULTS.bands.includes(b.m));
  const scored = m.PUBLISHED_FT.map(ft => m.scoreLength(
    m.fromDisplay(ft, 'ft'), bands, 'full', site, m.WIRE_RADIUS_M, 9));

  const passing = (tuner) => new Set(
    scored.map((s, i) => [s, i]).filter(([s]) => m.isGoodScore(s, tuner))
      .map(([, i]) => i));
  const rig = passing('rig');
  const wide = passing('wide');
  const roller = passing('roller');
  for (const i of rig) assert.ok(wide.has(i), 'rig ATU passes imply external');
  for (const i of wide) assert.ok(roller.has(i), 'external passes imply roller');
  assert.ok(roller.size >= wide.size && wide.size >= rig.size,
    `nested: rig ${rig.size} <= wide ${wide.size} <= roller ${roller.size}`);
});

test('every tuner preset states a limit a tuner could plausibly have', () => {
  for (const [key, def] of Object.entries(m.TUNERS)) {
    assert.ok(def.limit > 1, `${key}: the limit is a real SWR`);
    assert.ok(def.limit <= 30, `${key}: the limit is not fantasy`);
  }
  // The buttons show the ratio, so the presets must be distinguishable by it.
  const limits = Object.values(m.TUNERS).map(t => t.limit);
  assert.equal(new Set(limits).size, limits.length, 'no two presets share a limit');
  assert.ok(m.DEFAULT_TUNER in m.TUNERS, 'the default is a real preset');
});

test('the verdict follows the worst band, not the average', () => {
  // The failure this replaced: a mean under the limit while one band sat far
  // above it.  A scored length whose worst band exceeds the tuner cannot be
  // good however low its average is.
  const scored = { swr: 1.2, worst: { swr: 99 } };
  assert.equal(m.isGoodScore(scored, 'roller'), false,
    'a great average does not rescue an unmatched band');
  assert.equal(m.isGoodScore({ swr: 4.9, worst: { swr: 4.9 } }, 'wide'), true,
    'a length inside the limit on every band is good');
});

// ---- NEC deck export ----

/** Cards of one kind, split into fields, from a deck. */
const cardsOf = (deck, name) => deck.split('\n')
  .filter(line => line.startsWith(`${name} `))
  .map(line => line.split(/\s+/));

const defaultDeck = () => {
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bands = m.bandsIn('us').filter(b => m.DEFAULTS.bands.includes(b.m));
  return m.buildNecDeck(m.fromDisplay(71, 'ft'), bands, 'full', site,
                        m.WIRE_RADIUS_M);
};

test('the deck describes the geometry the model was fitted at', async () => {
  // Checked against the fixture the browser run was always meant to be held
  // to, nec/random_wire/reference_cases.json, so the deck and the PyNEC runs
  // behind the coefficients describe one antenna.  Its return_ft is the
  // horizontal run alone, which is exactly what counterpoiseM is.
  const { readFile } = await import('node:fs/promises');
  const url = new URL('../../nec/random_wire/reference_cases.json', import.meta.url);
  const fixture = JSON.parse(await readFile(url, 'utf8'));

  close(m.WIRE_RADIUS_M, fixture.wire_radius_m, 5e-7, 'wire radius');
  close(m.DEFAULT_COUNTERPOISE_Z_M, fixture.return_height_m, 1e-12,
    'the default counterpoise height is the one the fixture was solved at');
  assert.equal(m.DECK_SEGMENTS_PER_WAVELENGTH, fixture.segments_per_wavelength,
    'segmentation rule');

  const bands = m.bandsIn('us').filter(b => [40, 20, 15, 10].includes(b.m));
  for (const kase of fixture.cases) {
    const heightM = m.fromDisplay(kase.height_ft, 'ft');
    const runM = m.fromDisplay(kase.return_ft, 'ft');
    const lenM = m.fromDisplay(kase.length_ft, 'ft');
    const site = { geometry: 'flatTop', heightM, balunM: m.DEFAULT_BALUN_M,
                   counterpoiseM: runM, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M,
                   soil: kase.soil };
    const deck = m.buildNecDeck(lenM, bands, 'full', site, m.WIRE_RADIUS_M);

    const [antenna, drop, run] = cardsOf(deck, 'GW');
    const at = (card, i) => Number(card[i]);
    close(at(antenna, 5), heightM, 5e-4, `${kase.name}: wire height`);
    close(at(antenna, 6), lenM, 5e-4, `${kase.name}: wire length`);
    close(at(antenna, 8), heightM, 5e-4, `${kase.name}: wire stays level`);
    close(at(antenna, 9), m.WIRE_RADIUS_M, 5e-7, `${kase.name}: radius`);

    close(at(drop, 5), heightM, 5e-4, `${kase.name}: drop starts at the feedpoint`);
    close(at(drop, 8), m.DEFAULT_COUNTERPOISE_Z_M, 5e-4, `${kase.name}: drop ends low`);

    close(at(run, 5), m.DEFAULT_COUNTERPOISE_Z_M, 5e-4, `${kase.name}: run is low`);
    close(at(run, 6), runM, 5e-4, `${kase.name}: run length`);
    close(at(run, 8), m.DEFAULT_COUNTERPOISE_Z_M, 5e-4, `${kase.name}: run is level`);
    // Same direction as the antenna, per the fixture's geometry note.
    assert.ok(at(run, 6) > 0, `${kase.name}: run heads along the wire`);

    const [ground] = cardsOf(deck, 'GN');
    assert.equal(ground[1], '2',
      `${kase.name}: Sommerfeld ground, not the perfect plane of GN 1`);
    close(Number(ground[5]), kase.ground.eps, 1e-9, `${kase.name}: permittivity`);
    close(Number(ground[6]), kase.ground.sigma_s_per_m, 1e-9,
      `${kase.name}: conductivity`);
  }
});

test('the soil constants are the ones the fit was run at', async () => {
  // The page inlines them; nec/random_wire/nec_model.py is where they came
  // from, and a deck built at some other soil would ask NEC a question the
  // coefficients cannot be compared against.
  const { readFile } = await import('node:fs/promises');
  const url = new URL('../../nec/random_wire/nec_model.py', import.meta.url);
  const source = await readFile(url, 'utf8');
  for (const [key, soil] of Object.entries(m.SOILS)) {
    const line = new RegExp(`"${key}": \\(([\\d.]+), ([\\d.]+)\\)`).exec(source);
    assert.ok(line, `${key} appears in nec_model.py`);
    close(soil.epsR, Number(line[1]), 1e-9, `${key}: permittivity`);
    close(soil.sigmaSm, Number(line[2]), 1e-9, `${key}: conductivity`);
  }
});

test('the deck sweeps every selected band and nothing outside them', () => {
  const bands = m.bandsIn('us').filter(b => [40, 20, 15, 10].includes(b.m));
  const sweep = m.deckSweep(bands, 'full');
  const edges = bands.map(b => m.bandEdgesHz(b, 'full'));
  const lowest = Math.min(...edges.map(([lo]) => lo));
  const highest = Math.max(...edges.map(([, hi]) => hi));
  close(sweep.startHz, lowest, 1, 'the sweep starts at the lowest band edge');
  close(sweep.startHz + sweep.stepHz * (sweep.points - 1), highest, 1,
    'and ends at the highest');

  const [frequency] = cardsOf(defaultDeck(), 'FR');
  assert.equal(Number(frequency[2]), sweep.points, 'FR carries the point count');
  close(Number(frequency[5]) * 1e6, sweep.startHz, 1e3, 'FR starts in MHz');
  close(Number(frequency[6]) * 1e6, sweep.stepHz, 1e3, 'FR steps in MHz');
});

test('a one-band selection sweeps that band alone', () => {
  const bands = m.bandsIn('us').filter(b => b.m === 20);
  const sweep = m.deckSweep(bands, 'full');
  const [lo, hi] = m.bandEdgesHz(bands[0], 'full');
  close(sweep.startHz, lo, 1, 'starts at the band edge');
  close(sweep.startHz + sweep.stepHz * (sweep.points - 1), hi, 1, 'ends at it');
});

test('segments are odd, bounded, and short against the shortest wave', () => {
  // Odd so a centre segment exists, and dense enough at the top of the sweep,
  // where segments are electrically longest.  The source sits on segment 1 of
  // tag 1, so a wire described by too few segments moves the feedpoint.
  const bands = m.bandsIn('us').filter(b => [40, 10].includes(b.m));
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const deck = m.buildNecDeck(m.fromDisplay(203, 'ft'), bands, 'full', site,
                              m.WIRE_RADIUS_M);
  const topHz = Math.max(...bands.map(b => m.bandEdgesHz(b, 'full')[1]));
  const wavelengthM = m.C_SPEED / topHz;
  for (const wire of cardsOf(deck, 'GW')) {
    const segments = Number(wire[2]);
    const lengthM = Math.hypot(Number(wire[6]) - Number(wire[3]),
                               Number(wire[8]) - Number(wire[5]));
    assert.equal(segments % 2, 1, 'odd segment count');
    assert.ok(segments <= m.DECK_MAX_SEGMENTS, 'inside the cap');
    if (segments < m.DECK_MAX_SEGMENTS) {
      assert.ok(segments >= m.DECK_SEGMENTS_PER_WAVELENGTH * lengthM / wavelengthM - 1,
        `${lengthM.toFixed(1)} m wire has ${segments} segments`);
    }
  }
});

test('the deck feeds the end of the antenna wire and ends properly', () => {
  const deck = defaultDeck();
  const [excitation] = cardsOf(deck, 'EX');
  assert.deepEqual(excitation.slice(0, 4), ['EX', '0', '1', '1'],
    'a voltage source on segment 1 of the antenna wire');
  assert.ok(deck.startsWith('CM '), 'the deck opens with a comment');
  assert.ok(deck.includes('\nCE\n'), 'comments are terminated');
  assert.ok(deck.includes('\nGE 1\n'), 'geometry completes over a ground plane');
  // NEC-2 solves at an execution card, not at FR.  A deck that went FR / EN
  // was well formed, loaded, and computed nothing: nec2c echoed the geometry
  // and stopped.
  assert.ok(deck.includes('\nXQ\n'), 'something tells NEC to run');
  assert.ok(deck.endsWith('EN\n'), 'and the deck ends');
});

test('a deck needs a length and a band', () => {
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bands = m.bandsIn('us').filter(b => b.m === 20);
  assert.equal(m.buildNecDeck(0, bands, 'full', site, m.WIRE_RADIUS_M), null,
    'no wire, no deck');
  assert.equal(m.buildNecDeck(20, [], 'full', site, m.WIRE_RADIUS_M), null,
    'no band, no sweep');
  assert.equal(m.deckSweep([], 'full'), null, 'and no sweep to describe');
});

test('the AntennaSim project describes the same antenna as the deck', () => {
  // Two exports, one geometry.  They share deckWires precisely so this can
  // never drift, and this is what says so.
  const site = { geometry: 'flatTop', heightM: m.DEFAULT_HEIGHT_M, balunM: m.DEFAULT_BALUN_M,
    counterpoiseM: m.DEFAULT_COUNTERPOISE_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M,
    soil: 'poor' };
  const bands = m.bandsIn('us').filter(b => [40, 20, 15, 10].includes(b.m));
  const lenM = m.fromDisplay(71, 'ft');
  const project = JSON.parse(m.buildAntennaSimProject(
    lenM, bands, 'full', site, m.WIRE_RADIUS_M, '2026-01-01T00:00:00.000Z'));
  const deck = m.buildNecDeck(lenM, bands, 'full', site, m.WIRE_RADIUS_M);

  const wires = cardsOf(deck, 'GW');
  assert.equal(project.editor.wires.length, wires.length, 'same wire count');
  for (const [i, wire] of project.editor.wires.entries()) {
    const card = wires[i];
    assert.equal(wire.tag, Number(card[1]), `wire ${i}: tag`);
    assert.equal(wire.segments, Number(card[2]), `wire ${i}: segments`);
    const coordinates = [wire.x1, wire.y1, wire.z1, wire.x2, wire.y2, wire.z2];
    for (const [j, value] of coordinates.entries()) {
      close(value, Number(card[3 + j]), 5e-4, `wire ${i}: coordinate ${j}`);
    }
    close(wire.radius, Number(card[9]), 5e-7, `wire ${i}: radius`);
  }

  // The soil is the whole reason this format is written: their .nec importer
  // reads the ground card's type and drops its constants.
  assert.equal(project.editor.ground.type, 'custom', 'custom ground');
  close(project.editor.ground.custom_permittivity, m.SOILS.poor.epsR, 1e-9,
    'permittivity survives');
  close(project.editor.ground.custom_conductivity, m.SOILS.poor.sigmaSm, 1e-9,
    'conductivity survives');

  const sweep = m.deckSweep(bands, 'full');
  close(project.editor.frequencyRange.start_mhz, sweep.startHz / 1e6, 1e-6,
    'sweep start');
  close(project.editor.frequencyRange.stop_mhz,
    (sweep.startHz + sweep.stepHz * (sweep.points - 1)) / 1e6, 1e-6,
    'sweep stop');
  assert.equal(project.editor.frequencyRange.steps, sweep.points, 'sweep steps');

  const [lowLo, lowHi] = m.bandEdgesHz(
    bands.reduce((a, b) => (a.m > b.m ? a : b)), 'full');
  close(project.editor.designFrequencyMhz * 1e6, (lowLo + lowHi) / 2, 1,
    'the design frequency is the centre of the lowest band');
});

test('the AntennaSim project carries the fields its loader demands', () => {
  // Their format, their rules: an editor project needs a version their loader
  // will not reject, mode "editor", at least one wire, and a junctions array.
  // Nothing here can catch a schema change upstream -- see the note in the
  // page -- but a field dropped on this side is caught.
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bands = m.bandsIn('us').filter(b => b.m === 20);
  const project = JSON.parse(m.buildAntennaSimProject(
    m.fromDisplay(71, 'ft'), bands, 'full', site, m.WIRE_RADIUS_M,
    '2026-01-01T00:00:00.000Z'));

  assert.equal(project.version, m.ANTENNASIM_SCHEMA_VERSION, 'schema version');
  assert.equal(project.mode, 'editor', 'an editor project, not a template');
  assert.equal(typeof project.app_version, 'string', 'app_version is a string');
  assert.equal(project.created_at, '2026-01-01T00:00:00.000Z', 'timestamp');
  assert.ok(Array.isArray(project.editor.junctions), 'junctions array');
  assert.ok(project.editor.wires.length > 0, 'at least one wire');
  assert.deepEqual(project.editor.excitations,
    [{ wire_tag: 1, segment: 1, voltage_real: 1, voltage_imag: 0 }],
    'fed at the end of the antenna wire');
  assert.deepEqual(project.editor.loads, [], 'no loads');
  assert.deepEqual(project.editor.transmissionLines, [], 'no lines');
});

test('the project file needs a length and a band, as the deck does', () => {
  const site = { geometry: 'flatTop', balunM: m.DEFAULT_BALUN_M, counterpoiseZM: m.DEFAULT_COUNTERPOISE_Z_M, heightM: m.DEFAULT_HEIGHT_M, counterpoiseM: m.DEFAULT_COUNTERPOISE_M,
    soil: m.DEFAULT_SOIL };
  const bands = m.bandsIn('us').filter(b => b.m === 20);
  const at = '2026-01-01T00:00:00.000Z';
  assert.equal(
    m.buildAntennaSimProject(0, bands, 'full', site, m.WIRE_RADIUS_M, at), null,
    'no wire, no project');
  assert.equal(
    m.buildAntennaSimProject(20, [], 'full', site, m.WIRE_RADIUS_M, at), null,
    'no band, no sweep');
});
