// Pull the JSX out of a single-file page so tsc can type check it.
//
// The pages are self-contained HTML with the app in a <script type="text/babel">
// block; that is the shipped artifact and nothing here changes it.  The
// extracted file is generated, gitignored, and exists only for the checker.
//
// Line numbers are preserved: the script body is padded with blank lines so a
// diagnostic at line N of the .jsx is line N of the .html.

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const SCRIPT_RE = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;

/**
 * The app is the largest inline block: the pages also carry small loader
 * scripts, and which one is the app differs per page (text/babel where Babel
 * transpiles JSX, a bare <script> where it does not).
 *
 * @param {string} html
 * @returns {{body: string, startLine: number}}
 */
export function extractScript(html) {
  let best = null;
  for (const match of html.matchAll(SCRIPT_RE)) {
    if (/\bsrc=/i.test(match[1])) continue;   // external, nothing to check
    if (best === null || match[2].length > best[2].length) best = match;
  }
  if (best === null) throw new Error('no inline <script> block found');
  const startLine = html.slice(0, best.index + best[0].indexOf('>') + 1)
    .split('\n').length;
  return { body: best[2], startLine };
}

const [source, target] = process.argv.slice(2);
if (!source || !target) {
  console.error('usage: extract.mjs <page.html> <out.jsx>');
  process.exit(2);
}

const html = await readFile(resolve(source), 'utf8');
const { body, startLine } = extractScript(html);
await mkdir(dirname(resolve(target)), { recursive: true });
// Each page is checked in its own module scope; as plain scripts they would
// share one global namespace and collide on every common identifier.
await writeFile(resolve(target),
  '\n'.repeat(startLine - 1) + body.replace(/^\n/, '') + '\nexport {};\n');
