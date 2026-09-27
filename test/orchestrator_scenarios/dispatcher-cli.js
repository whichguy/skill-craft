'use strict';

// Shared public-CLI helpers for dispatcher scenario suites. Every call is a cold
// process from an unrelated directory; PLAN_DISPATCHER_DIR selects the package.

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');

const pkg = path.resolve(process.env.PLAN_DISPATCHER_DIR ||
  path.join(__dirname, '../../skills/plan-dispatcher'));
const helper = path.join(pkg, 'scripts/dispatch.js');
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

function makeRoot(prefix) {
  return fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), prefix)));
}

function saveJson(root, value, target) {
  const file = target || path.join(root, 'files', crypto.randomUUID() + '.json');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value));
  return file;
}

function evidence(root, value) {
  const file = saveJson(root, value);
  return { path: file, sha256: digest(fs.readFileSync(file)) };
}

function parse(child, expectFailure, label) {
  assert.ifError(child.error);
  if (expectFailure) {
    assert.notEqual(child.status, 0, label + ' unexpectedly succeeded');
    try { return JSON.parse(child.stderr); } catch (_) { return { error: child.stderr, code: 'UNPARSED' }; }
  }
  assert.equal(child.status, 0, label + ': ' + child.stderr);
  return JSON.parse(child.stdout);
}

function argvRun(argv, expectFailure = false) {
  const child = spawnSync(argv[0], argv.slice(1), { cwd: os.tmpdir(), encoding: 'utf8', timeout: 20000 });
  return parse(child, expectFailure, argv[2]);
}

function dispatch(root, operation, run, input, expectFailure = false) {
  let file;
  if (input !== undefined) {
    file = operation === 'report'
      ? saveJson(root, input, path.join(run, 'artifacts', input.attempt, 'envelope.json'))
      : saveJson(root, input);
  }
  return argvRun([process.execPath, helper, operation, run, ...(file ? [file] : [])], expectFailure);
}

// Fill "<...>" placeholders from `values` (keyed by field name); a placeholder
// starting "<omit" is removed unless `values` supplies that field.
function fill(template, values) {
  if (Array.isArray(template)) {
    return template.map((item) => fill(item, values));
  }
  if (template && typeof template === 'object') {
    const out = {};
    for (const [key, value] of Object.entries(template)) {
      const open = placeholders(value).length > 0;
      if (open && Object.hasOwn(values, key)) {
        out[key] = values[key];
      } else if (typeof value === 'string' && /^<.*>$/s.test(value)) {
        if (!value.startsWith('<omit')) {
          throw new Error('no value for placeholder field ' + key);
        }
      } else {
        out[key] = fill(value, values);
      }
    }
    return out;
  }
  if (typeof template === 'string' && /^<.*>$/s.test(template)) {
    throw new Error('placeholder inside an array needs a whole-field value: ' + template);
  }
  return template;
}

function placeholders(value, found = []) {
  if (typeof value === 'string' && /^<.*>$/s.test(value)) found.push(value);
  else if (value && typeof value === 'object') Object.values(value).forEach((item) => placeholders(item, found));
  return found;
}

// Run an exact call. `values` fills placeholders; nothing else is composed.
function runCall(root, callSpec, values = {}, expectFailure = false) {
  assert.ok(callSpec && Array.isArray(callSpec.argv), 'action must carry a call');
  if (!Object.hasOwn(callSpec, 'input')) {
    return argvRun(callSpec.argv, expectFailure);
  }
  const input = fill(callSpec.input, values);
  assert.deepEqual(placeholders(input), [], 'every placeholder must be filled');
  const file = saveJson(root, input, callSpec.input_path);
  return argvRun([...callSpec.argv, file], expectFailure);
}

function runAsync(argv) {
  return new Promise((resolve) => {
    const child = spawn(argv[0], argv.slice(1), { cwd: os.tmpdir() });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (data) => { stdout += data; });
    child.stderr.on('data', (data) => { stderr += data; });
    child.on('close', (status) => resolve({ status, stdout, stderr }));
  });
}

function contract(id) {
  return { task: 'Simulated task ' + id, ready: ['Inputs for ' + id + ' checked'], done: [id + ' verified'] };
}

function graphOf(steps) {
  return { version: 1, steps: steps.map(([id, deps]) => ({ id, deps, contract: contract(id) })) };
}

module.exports = {
  pkg, helper, digest, makeRoot, saveJson, evidence, argvRun, dispatch, fill, placeholders,
  runCall, runAsync, contract, graphOf,
};
