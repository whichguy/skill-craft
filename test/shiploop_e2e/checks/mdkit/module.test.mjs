import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

test('parse turns a heading into an h1 and plain text into a paragraph', async () => {
  const lib = await import(pathToFileURL(process.env.APP_MODULE).href);
  const heading = lib.marked.parse('# test');
  const paragraph = lib.marked.parse('just text');
  assert.equal(typeof heading, 'string');
  assert.equal(typeof paragraph, 'string');
  assert.match(heading, /<h1[^>]*>test<\/h1>/);
  assert.match(paragraph, /<p>just text<\/p>/);
  assert.doesNotMatch(paragraph, /<h1/);
});
