/**
 * Static file server for docs/, for the browser tests and for looking at a
 * page by hand.  Replaces `python3 -m http.server` so that one command
 * works wherever node does, and so the tests and a manual pass serve the
 * files identically.
 *
 * @example
 *   node serve.mjs          # http://127.0.0.1:4173/random-wire.html
 *   PORT=8000 node serve.mjs
 */

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

/** The directory served: docs/, one level up from tools/. */
const ROOT = fileURLToPath(new URL('..', import.meta.url));

const PORT = Number(process.env.PORT ?? 4173);

/** @type {Record<string, string>} */
const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

const server = createServer(async (request, response) => {
  const path = decodeURIComponent((request.url ?? '/').split('?')[0]);
  // normalize collapses any ".." before it can climb out of ROOT.
  const file = join(ROOT, normalize(path) === '/' ? 'index.html' : normalize(path));
  if (!file.startsWith(ROOT)) {
    response.writeHead(403);
    response.end('forbidden');
    return;
  }
  try {
    const body = await readFile(file);
    response.writeHead(200, {
      'content-type': CONTENT_TYPES[extname(file)] ?? 'application/octet-stream',
      // The tests assert on freshly edited files; never serve a stale one.
      'cache-control': 'no-store',
    });
    response.end(body);
  } catch {
    response.writeHead(404);
    response.end('not found');
  }
});

server.listen(PORT, '127.0.0.1', () => {
  process.stdout.write(`serving ${ROOT} at http://127.0.0.1:${PORT}/\n`);
});
