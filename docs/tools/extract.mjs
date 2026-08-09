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

const SCRIPT_RE = /<script\b[^>]*type=["']text\/babel["'][^>]*>([\s\S]*?)<\/script>/i;

/** @param {string} html @returns {{body: string, startLine: number}} */
export function extractScript(html) {
  const match = SCRIPT_RE.exec(html);
  if (!match) throw new Error('no <script type="text/babel"> block found');
  const startLine = html.slice(0, match.index + match[0].indexOf('>') + 1)
    .split('\n').length;
  return { body: match[1], startLine };
}

const [source, target] = process.argv.slice(2);
if (!source || !target) {
  console.error('usage: extract.mjs <page.html> <out.jsx>');
  process.exit(2);
}

const html = await readFile(resolve(source), 'utf8');
const { body, startLine } = extractScript(html);
await mkdir(dirname(resolve(target)), { recursive: true });
await writeFile(resolve(target), '\n'.repeat(startLine - 1) + body.replace(/^\n/, ''));
