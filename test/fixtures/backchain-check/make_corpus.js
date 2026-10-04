#!/usr/bin/env node
'use strict';

// Records Backchain's own verdicts for the ShipLoop port (shiploop_backchain_graph.py).
// Run by hand whenever the Backchain checkout's harness/lib.js changes, then commit the output:
//   BACKCHAIN_DEV_ROOT=/path/to/backchain node test/fixtures/backchain-check/make_corpus.js
// It copies the checkout's structural good and bad fixtures, keeps the committed luna/ and edge/ inputs, and writes
// <name>.verdict.json beside every input, ecmascript-whitespace.json and manifest.json.

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const root = process.env.BACKCHAIN_DEV_ROOT;
if (!root) {
  console.error('make_corpus: set BACKCHAIN_DEV_ROOT to the Backchain checkout');
  process.exit(2);
}
const libPath = path.join(root, 'harness', 'lib.js');
const lib = require(libPath);
const here = __dirname;
const sha256 = (data) => crypto.createHash('sha256').update(data).digest('hex');
const libSha = sha256(fs.readFileSync(libPath));
const write = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
const isInput = (name) => name.endsWith('.json') && !name.endsWith('.verdict.json') && name !== 'sources.json';

for (const kind of ['good', 'bad']) {
  const source = path.join(root, 'test', 'fixtures', 'structural', kind);
  const target = path.join(here, 'structural', kind);
  fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });
  for (const name of fs.readdirSync(source).filter(isInput).sort()) {
    fs.copyFileSync(path.join(source, name), path.join(target, name));
  }
}

function verdict(plan) {
  const packaged = lib.packagePlan(plan).plan;
  const structure = lib.validateStructure(packaged);
  const raw = lib.validateStructure(plan);
  return {
    ok: structure.ok,
    failures: structure.failures,
    completion: lib.completionStatus(packaged).status,
    parallel_groups: lib.computeParallelGroups(packaged),
    packaged_sha256: sha256(JSON.stringify(packaged)),
    unconfirmed_produces: lib.unconfirmedProduces(packaged),
    raw: { ok: raw.ok, failures: raw.failures, completion: lib.completionStatus(plan).status },
  };
}

const inputs = [];
for (const dir of ['structural/good', 'structural/bad', 'luna', 'edge']) {
  for (const name of fs.readdirSync(path.join(here, dir)).filter(isInput).sort()) {
    const relative = `${dir}/${name}`;
    const bytes = fs.readFileSync(path.join(here, relative));
    const record = { input: relative, input_sha256: sha256(bytes), lib_js_sha256: libSha,
      ...verdict(JSON.parse(bytes.toString('utf8'))) };
    write(path.join(here, dir, name.replace(/\.json$/, '.verdict.json')), record);
    inputs.push({ input: relative, sha256: record.input_sha256, ok: record.ok });
  }
}

// JS `\s` and String.prototype.trim use the same set; the port's whitespace class must equal it.
const whitespace = [];
for (let code = 0; code <= 0x10ffff; code += 1) {
  if (code >= 0xd800 && code <= 0xdfff) continue;
  const text = String.fromCodePoint(code);
  if (/^\s$/u.test(text) !== (text.trim() === '')) throw new Error(`\\s and trim disagree at ${code}`);
  if (text.trim() === '') whitespace.push(code);
}
write(path.join(here, 'ecmascript-whitespace.json'), { node: process.version, code_points: whitespace });

let commit = null;
try {
  commit = execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
} catch (error) {
  commit = null;
}
write(path.join(here, 'manifest.json'), {
  schema: 'shiploop-backchain-check-corpus/v1',
  lib_js_sha256: libSha,
  backchain_commit: commit,
  node: process.version,
  inputs,
});
console.log(`make_corpus: ${inputs.length} verdicts from lib.js ${libSha.slice(0, 12)}`);
