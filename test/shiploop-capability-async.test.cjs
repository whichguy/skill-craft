#!/usr/bin/env node
/* Calibrate the local client-ordering probe; this is not a browser/GAS test. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createHash} = require('node:crypto');

const fixture = path.join(__dirname, 'experiments/shiploop_capabilities/fixtures/client.html');
const source = fs.readFileSync(fixture, 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];

function replaceOnce(text, before, after) {
  assert.equal(text.split(before).length, 2, 'fixture changed: recalibrate the probe');
  return text.replace(before, after);
}

// An in-memory comparison only: no replacement library, application source
// change or remote write. The requirement is latest-issued refresh acceptance.
let extension = replaceOnce(source, 'let state;', 'let state; let latestRefresh = 0;');
extension = replaceOnce(extension, 'async function refresh() {',
  'async function refresh() { const request = ++latestRefresh;');
extension = replaceOnce(extension, 'state = await response.json();',
  'const incoming = await response.json(); if (request !== latestRefresh) return; state = incoming;');

async function observe(script, completionOrder) {
  const requests = [];
  const elements = new Map();
  const context = vm.createContext({
    document: {querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, {textContent: '', addEventListener() {}});
      return elements.get(selector);
    }},
    fetch(url) {
      assert.equal(url, '/api/state');
      return new Promise(resolve => requests.push(resolve));
    },
  });
  script = replaceOnce(script, '\nrefresh();', '\nglobalThis.initialRefresh = refresh();');
  vm.runInContext(script, context, {timeout: 1000});
  const pending = [context.initialRefresh, vm.runInContext('refresh()', context, {timeout: 1000})];
  assert.equal(requests.length, 2);
  const trace = [];
  for (const request of completionOrder) {
    const version = request + 2;
    requests[request]({json: async () => ({version, turn: version === 2 ? 'black' : 'red'})});
    await pending[request];
    trace.push({completedRequest: request, returnedVersion: version,
      renderedVersion: elements.get('#state')?.textContent
        ? JSON.parse(elements.get('#state').textContent).version : null,
      clientHeldVersion: vm.runInContext('state ? state.version : null', context, {timeout: 1000})});
  }
  return trace;
}

(async () => {
  const results = [];
  for (const [variant, script] of [['existing', source], ['minimal_sequence_extension', extension]]) {
    for (const [order, sequence] of [['ordinary', [0, 1]], ['reversed', [1, 0]]]) {
      const trace = await observe(script, sequence);
      const expected = variant === 'existing' && order === 'reversed' ? 2 : 3;
      assert.equal(trace.at(-1).renderedVersion, expected);
      assert.equal(trace.at(-1).clientHeldVersion, expected);
      results.push({variant, order, trace});
    }
  }
  process.stdout.write(JSON.stringify({passed: true, fidelity: 'local_mock',
    producer: {command: 'node test/shiploop-capability-async.test.cjs', runtime: process.version,
      client_sha256: createHash('sha256').update(fs.readFileSync(fixture)).digest('hex'),
      test_sha256: createHash('sha256').update(fs.readFileSync(__filename)).digest('hex')},
    finding: 'Existing reversed completion regresses rendered and client-held state; the sequence comparison retains the newer refresh.',
    limits: 'Synthetic DOM/fetch only; no browser, platform scheduling, service mutation, deployment or player access tested.',
    results}, null, 2) + '\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
