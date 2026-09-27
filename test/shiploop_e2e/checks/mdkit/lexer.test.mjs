import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(readFileSync(join(here, 'fixtures', 'lexer.json'), 'utf8'));
const lib = await import(pathToFileURL(process.env.APP_MODULE).href);
const { Marked, Lexer, Parser } = lib;

function render(check) {
  const marked = new Marked(check.options || {});
  const html = check.mode === 'inline' ? marked.parseInline(check.md) : marked.parse(check.md);
  assert.equal(typeof html, 'string');
  assert.equal(html, check.html);
  if (check.html.includes('<')) assert.match(html, /<[a-zA-Z]/);
  return html;
}

for (const spec of cases) {
  test(spec.name, () => {
    assert.ok(spec.checks.length > 0);
    for (const check of spec.checks) render(check);
  });
}

test('Lexer > multiple instances > successive lexer instances render the same HTML', () => {
  const parser = new Parser();
  const first = parser.parse(new Lexer().lex('Test'));
  const second = parser.parse(new Lexer().lex('Test'));
  assert.equal(typeof first, 'string');
  assert.equal(first, second);
  assert.equal(first, '<p>Test</p>\n');
});

test('Lexer > multiple instances > static lex and instance lex render the same HTML', () => {
  const parser = new Parser();
  const fromStatic = parser.parse(Lexer.lex('Test'));
  const fromInstance = parser.parse(new Lexer().lex('Test'));
  assert.equal(typeof fromStatic, 'string');
  assert.equal(fromStatic, fromInstance);
  assert.equal(fromStatic, '<p>Test</p>\n');
});
