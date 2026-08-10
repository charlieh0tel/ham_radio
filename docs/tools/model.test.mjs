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

test('display units round trip', () => {
  for (const unit of Object.keys(m.UNITS)) {
    const there = m.toDisplay(21.336, unit);
    close(m.fromDisplay(there, unit), 21.336, 1e-9, `round trip via ${unit}`);
  }
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
  // The constants were hand-copied from coefficients.py once.  A short or
  // misaligned row would interpolate silently against the wrong node.
  for (const [soil, coeffs] of Object.entries(m.MODEL_COEFFS)) {
    assert.ok(soil in m.SOILS, `${soil} is a known soil`);
    for (const [name, values] of Object.entries(coeffs)) {
      assert.equal(values.length, m.MODEL_H_NODES.length,
        `${soil}.${name} has one value per node`);
      assert.ok(values.every(Number.isFinite), `${soil}.${name} is all finite`);
    }
  }
  for (const soil of Object.keys(m.SOILS)) {
    assert.ok(soil in m.MODEL_COEFFS, `${soil} has coefficients`);
  }
  const rising = m.MODEL_H_NODES.every(
    (v, i) => i === 0 || v > m.MODEL_H_NODES[i - 1]);
  assert.ok(rising, 'nodes ascend, as interpCoeff assumes');
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
  const site = { heightM: 9.144, returnM: 7.62, soil: 'average' };
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
  const site = { heightM: 9.144, returnM: 7.62, soil: 'average' };
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
    { heightM: 3, returnM: 7.62, soil: 'average' }, m.WIRE_RADIUS_M);
  const high = m.endFedZin(lenM, freqHz,
    { heightM: 20, returnM: 7.62, soil: 'average' }, m.WIRE_RADIUS_M);
  assert.ok(Math.abs(Math.hypot(low.re, low.im) - Math.hypot(high.re, high.im)) > 1,
    'height moves the feedpoint');
});

test('suggested lengths are ordered, distinct and long enough', () => {
  const site = { heightM: m.DEFAULT_HEIGHT_M, returnM: m.DEFAULT_RETURN_M,
    soil: m.DEFAULT_SOIL };
  const out = m.solveImpedance('us', [80, 40, 20, 15, 10], 'full', site,
    m.WIRE_RADIUS_M, 9, 60);
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
  const site = { heightM: m.DEFAULT_HEIGHT_M, returnM: m.DEFAULT_RETURN_M,
    soil: m.DEFAULT_SOIL };
  const out = m.solveImpedance('us', [], 'full', site, m.WIRE_RADIUS_M, 9, 30);
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

test('raw avoid intervals are ordered and bounded', () => {
  // avoidIntervals returns one zone per band per multiple; overlap between
  // bands is expected here and resolved by solve().
  const bands = m.bandsIn('us').filter(b => [40, 20, 15].includes(b.m));
  for (const interval of m.avoidIntervals(bands, 'full', 0.95, 8, 60)) {
    assert.ok(interval.lo < interval.hi, 'each zone is ordered');
    assert.ok(interval.lo >= 0, 'no negative length');
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

test('usable spans and avoid zones tile the axis without overlapping', () => {
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
  const site = { heightM: 9.144, returnM: 7.62, soil: 'average' };
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
    const z = m.endFedZin(20, freqHz, { heightM: 9.144, returnM: 7.62, soil },
      m.WIRE_RADIUS_M);
    assert.ok(Number.isFinite(z.re) && z.re > 0, `${soil} gives a real impedance`);
  }
});

test('SWR is never below one and rises away from a match', () => {
  for (const ohms of [5, 50, 450, 2450, 10000]) {
    const swr = m.swrAtRadio({ re: ohms, im: 0 }, 9);
    assert.ok(swr >= 1 - 1e-9, `SWR >= 1 at ${ohms} ohms`);
    assert.ok(Number.isFinite(swr), `SWR finite at ${ohms} ohms`);
  }
  const matched = m.swrAtRadio({ re: 450, im: 0 }, 9);
  const reactive = m.swrAtRadio({ re: 450, im: 450 }, 9);
  assert.ok(reactive > matched, 'reactance makes the match worse');
});

test('scoring a length returns a mean bounded by its own worst case', () => {
  const site = { heightM: 9.144, returnM: 7.62, soil: 'average' };
  const bands = m.bandsIn('us').filter(b => [40, 20, 10].includes(b.m));
  const scored = m.scoreLength(21.6, bands, 'full', site, m.WIRE_RADIUS_M, 9);
  assert.ok(scored !== null, 'a score comes back');
  assert.ok(scored.swr >= 1, 'geometric mean is a ratio');
  assert.ok(scored.worst.swr >= scored.swr, 'the worst band is at least the mean');
  assert.ok(bands.some(b => b.m === scored.worst.band.m),
    'the worst band is one that was asked for');
});

test('a longer return path changes the score', () => {
  // Finding 4: the return resonates in its own right.  A model that treated
  // it as a passive ground would return the same number twice.
  const bands = m.bandsIn('us').filter(b => [40, 20].includes(b.m));
  const short = m.scoreLength(21.6, bands, 'full',
    { heightM: 9.144, returnM: 3, soil: 'average' }, m.WIRE_RADIUS_M, 9);
  const long = m.scoreLength(21.6, bands, 'full',
    { heightM: 9.144, returnM: 30, soil: 'average' }, m.WIRE_RADIUS_M, 9);
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
