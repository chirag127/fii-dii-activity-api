// Guard: no legacy "oriz" branding/domain anywhere in tracked source.
// The project name is strictly "FII/DII Activity API".
// Run: node --test
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const SKIP_DIRS = new Set(['node_modules', '.git', 'dist', '.wrangler']);
const CHECK_EXT = /\.(md|mjs|js|json|yaml|yml|svg|css|html|txt)$/i;

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) yield* walk(full);
    else if (CHECK_EXT.test(entry)) yield full;
  }
}

// These test files must reference the banned word to check for it; skip them.
const SELF = new Set(['scripts/no-oriz.test.mjs', 'scripts/openapi.test.mjs']);

test('no file contains the legacy brand string', () => {
  // Build the needle from fragments so THIS file doesn't contain the literal.
  const needle = 'or' + 'iz';
  const re = new RegExp(needle, 'i');
  // The guard script's own filename legitimately contains the fragment; strip
  // references to it (e.g. in README docs) before scanning.
  const filenameToken = new RegExp('no-' + needle + '\\.test\\.mjs', 'gi');
  // The sanctioned GitHub-Pages custom domain (<repo>.oriz.in) legitimately
  // contains the fragment; strip it before scanning. Bare repo NAMES stay
  // brand-free; only the .oriz.in DOMAIN is allowed.
  const domainToken = new RegExp(
    '[a-z0-9-]+\\.' + needle + '\\.in',
    'gi',
  );
  const offenders = [];
  for (const file of walk(root)) {
    const rel = relative(root, file).replace(/\\/g, '/');
    if (SELF.has(rel)) continue;
    const text = readFileSync(file, 'utf8')
      .replace(filenameToken, '')
      .replace(domainToken, '');
    if (re.test(text)) offenders.push(rel);
  }
  assert.deepEqual(offenders, [], `legacy brand found in: ${offenders.join(', ')}`);
});
