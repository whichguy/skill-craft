'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createProperties, loadRuntime, plain } = require('./local-runtime.cjs');
const { identity } = require('../scripts/verify.cjs');

const PREFIX = '__shiploop_repeatable_v1__';
const FULL = ['TC-01', 'TC-02', 'TC-03', 'TC-04'];

function assertResult(result, ids, counts) {
  const actual = plain(result);
  assert.equal(actual.suiteId, 'shiploop-remote-repeatability-v1');
  assert.equal(actual.testDefinitionRevision, 'repeatable-tests-v1');
  assert.equal(actual.sourceRevision, identity());
  assert.deepEqual(actual.selectedIds, ids);
  assert.deepEqual(actual.executedIds, ids);
  assert.deepEqual(actual.cases.map((entry) => entry.id), ids);
  assert.deepEqual(actual.summary, counts);
  for (const outcome of ['passed', 'failed', 'blocked']) {
    assert.equal(actual.cases.filter((entry) => entry.outcome === outcome).length, counts[outcome]);
  }
  assert.equal(Object.values(counts).reduce((sum, n) => sum + n, 0), ids.length);
  return actual;
}

function assertClean(runtime, unrelated = { unrelated: 'preserve-me' }) {
  assert.deepEqual(plain(runtime.suite.inspectOwnedState()), { prefix: PREFIX, keys: [], count: 0 });
  assert.deepEqual(Object.fromEntries(runtime.properties.values), unrelated);
}

test('T-01 exact integer-cent results and invalid inputs use independent oracles', () => {
  const { fixture: { totalCents } } = loadRuntime();
  for (const [quantity, unitCents, expected] of [
    [0, 499, 0], [4, 0, 0], [1, 1, 1], [3, 499, 1497], [17, 235, 3995],
    [9007199254740991, 1, 9007199254740991], [9007199254740992, 1, 9007199254740992],
  ]) assert.equal(totalCents(quantity, unitCents), expected);
  for (const invalid of [true, false, -1, -0.5, 0.5, NaN, Infinity, -Infinity, '2', '', null, undefined, {}, [], 2n]) {
    assert.throws(() => totalCents(invalid, 2), /./);
    assert.throws(() => totalCents(2, invalid), /./);
  }
  assert.throws(() => totalCents(), /./);
});

test('T-02 full runs, reruns and explicit reverse order leave no residue', () => {
  const runtime = loadRuntime({ properties: createProperties({ unrelated: 'preserve-me' }) });
  for (const selection of ['full', 'full', [...FULL].reverse(), { ids: ['TC-03'] }, { ids: ['TC-03'] }]) {
    const ids = Array.isArray(selection) ? selection : typeof selection === 'object' ? selection.ids : FULL;
    const result = assertResult(runtime.suite.runRepeatableTests(selection), ids, { passed: ids.length, failed: 0, blocked: 0 });
    assert.equal(result.selection, selection === 'full' ? 'full' : 'explicit');
    for (const entry of result.cases.filter((entry) => ['TC-03', 'TC-04'].includes(entry.id))) {
      assert.equal(entry.setup, 'passed');
      assert.equal(entry.teardown, 'passed');
      assert.equal(entry.cleanup.removed, true);
    }
    assertClean(runtime);
  }
  const created = runtime.properties.calls.filter((call) => call.operation === 'setProperty').map((call) => call.key);
  assert.ok(created.every((key) => key.startsWith(PREFIX)));
  // TC-04 may update the same key, but each invocation must have its own keys.
  const invocations = [];
  for (let i = 0; i < 2; i++) invocations.push(runtime.suite.runRepeatableTests(['TC-03']).invocationId);
  assert.notEqual(invocations[0], invocations[1]);
  assertClean(runtime);
});

test('T-04 smoke, defaults and every durable ID are registered and independently selectable', () => {
  const runtime = loadRuntime({ properties: createProperties({ unrelated: 'preserve-me' }) });
  for (const selection of ['smoke', { suite: 'smoke' }]) {
    const result = assertResult(runtime.suite.runRepeatableTests(selection), ['TC-01', 'TC-03'], { passed: 2, failed: 0, blocked: 0 });
    assert.equal(result.selection, 'smoke');
  }
  for (const selection of [undefined, { suite: 'full' }]) {
    assertResult(runtime.suite.runRepeatableTests(selection), FULL, { passed: 4, failed: 0, blocked: 0 });
  }
  for (const id of FULL) assertResult(runtime.suite.runRepeatableTests([id]), [id], { passed: 1, failed: 0, blocked: 0 });
  assertClean(runtime);
});

test('T-04 malformed, empty, duplicate and unknown selections reject before state access', () => {
  const runtime = loadRuntime();
  for (const selection of ['UNKNOWN', ['UNKNOWN'], ['TC-03', 'UNKNOWN'], [], ['TC-01', 'TC-01'],
    null, true, 7, {}, { ids: [] }, { ids: 'TC-01' }, { suite: 'no' }, { suite: 'full', ids: ['TC-01'] },
    { suite: 'full', extra: true }, [1], ['toString'], ['__proto__']]) {
    assert.throws(() => runtime.suite.runRepeatableTests(selection), /./, JSON.stringify(selection));
  }
  assert.deepEqual(runtime.properties.calls, []);
});

test('T-03 NC-01 setup and NC-02 assertion failures remain failures, clean up and recover', () => {
  const runtime = loadRuntime({ properties: createProperties({ unrelated: 'preserve-me' }) });
  for (const [id, phase] of [['NC-01', 'setup'], ['NC-02', 'assertion']]) {
    for (let repeat = 0; repeat < 2; repeat++) {
      const result = assertResult(runtime.suite.runRepeatableTests([id]), [id], { passed: 0, failed: 1, blocked: 0 });
      const entry = result.cases[0];
      assert.ok(entry.errors.some((error) => error.phase === phase && error.message.length));
      assert.equal(entry.setup, phase === 'setup' ? 'failed' : 'passed');
      assert.equal(entry.teardown, 'passed');
      assert.equal(entry.cleanup.removed, true);
      assertClean(runtime);
    }
  }
  assertResult(runtime.suite.runRepeatableTests('full'), FULL, { passed: 4, failed: 0, blocked: 0 });
  assertClean(runtime);
});

test('T-05 missing service blocks only stateful cases, while pure cases still execute', () => {
  const runtime = loadRuntime({ globals: { PropertiesService: undefined } });
  const result = assertResult(runtime.suite.runRepeatableTests('full'), FULL, { passed: 2, failed: 0, blocked: 2 });
  assert.ok(result.cases.slice(2).every((entry) => entry.errors.some((error) => error.phase === 'dependency')));
  assert.throws(() => runtime.suite.inspectOwnedState(), /./);
  assert.deepEqual(runtime.properties.calls, []);
});

test('T-05 denied service acquisition and missing UUID capability cannot produce a false pass', () => {
  for (const globals of [
    { PropertiesService: { getScriptProperties() { throw new Error('simulated access denied'); } } },
    { Utilities: undefined },
  ]) {
    const runtime = loadRuntime({ globals });
    assertResult(runtime.suite.runRepeatableTests(['TC-03', 'TC-01']), ['TC-03', 'TC-01'], { passed: 1, failed: 0, blocked: 1 });
    assert.equal(runtime.properties.values.size, 0);
  }
});

test('T-05 partial setup write then error still removes the sentinel', () => {
  const properties = createProperties({ unrelated: 'preserve-me' }, ({ operation, key, value, values }) => {
    if (operation === 'setProperty') {
      values.set(key, String(value));
      throw new Error('simulated failure after write');
    }
  });
  const runtime = loadRuntime({ properties });
  for (let repeat = 0; repeat < 2; repeat++) {
    const result = assertResult(runtime.suite.runRepeatableTests(['TC-03']), ['TC-03'], { passed: 0, failed: 1, blocked: 0 });
    assert.ok(result.cases[0].errors.some((error) => error.phase === 'setup' && /after write/.test(error.message)));
    assert.equal(result.cases[0].cleanup.removed, true);
    assertClean(runtime);
  }
});

test('T-05 cleanup error preserves primary failure and read-only inspection reveals residue', () => {
  const properties = createProperties({ unrelated: 'preserve-me' }, ({ operation }) => {
    if (operation === 'deleteProperty') throw new Error('simulated deletion denied');
  });
  const runtime = loadRuntime({ properties });
  const result = assertResult(runtime.suite.runRepeatableTests(['NC-02']), ['NC-02'], { passed: 0, failed: 1, blocked: 0 });
  const entry = result.cases[0];
  assert.equal(entry.teardown, 'failed');
  assert.ok(entry.errors.some((error) => error.phase === 'assertion'));
  assert.ok(entry.errors.some((error) => error.phase === 'teardown' && /deletion denied/.test(error.message)));
  const before = Object.fromEntries(properties.values);
  const callsBefore = properties.calls.length;
  const scan = plain(runtime.suite.inspectOwnedState());
  assert.equal(scan.count, 1);
  assert.deepEqual(scan.keys, [entry.cleanup.key]);
  assert.deepEqual(Object.fromEntries(properties.values), before);
  assert.deepEqual(properties.calls.slice(callsBefore).map((call) => call.operation), ['getProperties']);
  assert.equal(properties.values.get('unrelated'), 'preserve-me');
  // Local fake is owned by this test and discarded; remote residue would require recovery.
});

test('T-05 silent failed deletion is detected and never reported as passed', () => {
  const properties = createProperties({ unrelated: 'preserve-me' });
  properties.service.deleteProperty = () => properties.service;
  const runtime = loadRuntime({ properties });
  const result = assertResult(runtime.suite.runRepeatableTests(['TC-03']), ['TC-03'], { passed: 0, failed: 1, blocked: 0 });
  assert.equal(result.cases[0].teardown, 'failed');
  assert.equal(runtime.suite.inspectOwnedState().count, 1);
});

test('T-02/T-05 old interrupted and interleaved invocation state is preserved', () => {
  const oldKey = `${PREFIX}interrupted__TC-03`;
  let nested = false;
  let other;
  const properties = createProperties({ unrelated: 'preserve-me', [oldKey]: 'old-sentinel' }, ({ operation }) => {
    if (operation === 'setProperty' && !nested) {
      nested = true;
      assertResult(other.suite.runRepeatableTests(['TC-04']), ['TC-04'], { passed: 1, failed: 0, blocked: 0 });
    }
  });
  const runtime = loadRuntime({ properties });
  other = loadRuntime({ properties });
  assertResult(runtime.suite.runRepeatableTests(['TC-03']), ['TC-03'], { passed: 1, failed: 0, blocked: 0 });
  assert.ok(nested);
  assert.deepEqual(plain(runtime.suite.inspectOwnedState()).keys, [oldKey]);
  assert.deepEqual(Object.fromEntries(properties.values), { unrelated: 'preserve-me', [oldKey]: 'old-sentinel' });
  const keys = properties.calls.filter((call) => call.operation === 'setProperty').map((call) => call.key);
  assert.equal(new Set(keys).size, 2);
});
