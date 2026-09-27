import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(readFileSync(join(here, 'fixtures', 'parser.json'), 'utf8'));
const { Parser } = await import(pathToFileURL(process.env.APP_MODULE).href);

function revive(value) {
  if (Array.isArray(value)) return value.map(revive);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      out[key] = child === '__UNDEF__' ? undefined : revive(child);
    }
    return out;
  }
  return value;
}

for (const spec of cases) {
  test(spec.name, () => {
    const parser = new Parser(spec.options);
    const tokens = revive(spec.tokens);
    const html = spec.inline ? parser.parseInline(tokens) : parser.parse(tokens);
    assert.equal(typeof html, 'string');
    assert.equal(html, spec.html);
    if (spec.html.includes('<')) assert.match(html, /<[a-zA-Z]/);
    else assert.ok(html.length > 0);
  });
}
