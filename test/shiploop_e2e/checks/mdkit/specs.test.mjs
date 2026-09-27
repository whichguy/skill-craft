import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(readFileSync(join(here, 'fixtures', 'specs.json'), 'utf8'));
const { Marked } = await import(pathToFileURL(process.env.APP_MODULE).href);

for (const spec of cases) {
  test(spec.name, () => {
    const marked = new Marked(spec.options);
    const before = process.hrtime();
    const html = marked.parse(spec.markdown);
    const elapsed = process.hrtime(before);
    assert.equal(typeof html, 'string');
    assert.equal(html, spec.html);
    if (!spec.options.async && elapsed[0] > 0) {
      assert.fail('took too long: ' + (elapsed[0] + elapsed[1] * 1e-9).toFixed(3) + 's');
    }
  });
}
