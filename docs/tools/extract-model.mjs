// Pull the DOM-free part of a single-file page out as an ES module, so the
// logic can be exercised from the command line and in CI.
//
// The type checker (extract.mjs) proves the code compiles; nothing proved it
// computes.  That gap let the impedance mode draw half-wave lengths at one
// velocity factor while scoring against another, which typed cleanly and was
// wrong on screen.
//
// The page marks its own boundary with BEGIN PURE and END PURE.  Everything
// between is free of React, window and document; the extracted module appends
// an export list so tests can reach it.  The extracted file is generated and
// gitignored; the shipped HTML is untouched.

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

import { extractScript } from './extract.mjs';

const BEGIN = '// BEGIN PURE';
const END = '// END PURE';

/**
 * Names the tests import.  Explicit rather than inferred: an export list that
 * quietly tracks whatever the page happens to define would let a rename pass
 * unnoticed.
 */
const EXPORTS = [
  // constants
  'C_SPEED', 'FT_PER_M', 'UNITS', 'SOILS', 'REGIONS', 'SEGMENTS', 'MODES',
  'MODEL_H_NODES', 'MODEL_COEFFS', 'MODEL_VF_A', 'WIRE_RADIUS_M',
  'DEFAULT_VELOCITY_FACTOR', 'DEFAULT_HEIGHT_M', 'DEFAULT_RETURN_M',
  'DEFAULT_SOIL', 'DEFAULT_UNUN_RATIO', 'UNUN_RATIOS', 'Z_SYSTEM_OHMS',
  'PUBLISHED_FT', 'SWR_GOOD',
  'HEIGHT_RANGE_M', 'RETURN_RANGE_M',
  // length math
  'halfWaveM', 'bandsIn', 'bandEdgesHz', 'resonanceInterval', 'avoidIntervals',
  'tooShortM', 'solve', 'judgeLength',
  // impedance model
  'wireZ0', 'interpCoeff', 'lineZ', 'endFedZin', 'swrAtRadio', 'scoreLength',
  'solveImpedance',
  // display
  'toDisplay', 'fromDisplay', 'fmtLen',
];

/**
 * @param {string} body  the full script body
 * @returns {string} the marked region
 */
export function pureRegion(body) {
  const start = body.indexOf(BEGIN);
  const end = body.indexOf(END);
  if (start === -1 || end === -1) {
    throw new Error(`page is missing ${BEGIN} / ${END} markers`);
  }
  if (end < start) throw new Error(`${END} precedes ${BEGIN}`);
  return body.slice(start + BEGIN.length, end);
}

const [source, target] = process.argv.slice(2);
if (!source || !target) {
  console.error('usage: extract-model.mjs <page.html> <out.mjs>');
  process.exit(2);
}

const html = await readFile(resolve(source), 'utf8');
const { body } = extractScript(html);
const region = pureRegion(body);
await mkdir(dirname(resolve(target)), { recursive: true });
await writeFile(resolve(target), `${region}\nexport { ${EXPORTS.join(', ')} };\n`);
