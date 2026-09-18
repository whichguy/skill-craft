function _main(module = globalThis.__getCurrentModule(), exports = module.exports) {
  const PREFIX = '__shiploop_repeatable_v1__';
  const FULL_IDS = ['TC-01', 'TC-02', 'TC-03', 'TC-04'];
  const SMOKE_IDS = ['TC-01', 'TC-03'];
  const ALL_IDS = FULL_IDS.concat(['NC-01', 'NC-02']);

  function parseSelection(selection) {
    let requested = selection === undefined ? 'full' : selection;
    if (requested !== null && typeof requested === 'object' && !Array.isArray(requested)) {
      const keys = Object.keys(requested);
      if (keys.length !== 1 || (keys[0] !== 'ids' && keys[0] !== 'suite')) {
        throw new TypeError('Invalid selection: use {ids: [...]} or {suite: "full"|"smoke"}');
      }
      if (keys[0] === 'ids') {
        if (!Array.isArray(requested.ids)) {
          throw new TypeError('Invalid selection: ids must be an array');
        }
        requested = requested.ids;
      } else {
        if (requested.suite !== 'full' && requested.suite !== 'smoke') {
          throw new TypeError('Invalid selection: suite must be full or smoke');
        }
        requested = requested.suite;
      }
    }
    if (requested === 'full') return { name: 'full', ids: FULL_IDS.slice() };
    if (requested === 'smoke') return { name: 'smoke', ids: SMOKE_IDS.slice() };
    if (!Array.isArray(requested) || requested.length === 0) {
      throw new TypeError('Invalid selection: expected full, smoke, or a nonempty ID array');
    }
    const ids = [];
    for (let index = 0; index < requested.length; index += 1) {
      const id = requested[index];
      if (typeof id !== 'string' || ALL_IDS.indexOf(id) === -1) {
        throw new TypeError('Invalid selection: unknown test ID at index ' + index);
      }
      if (ids.indexOf(id) !== -1) throw new TypeError('Invalid selection: duplicate test ID ' + id);
      ids.push(id);
    }
    return { name: 'explicit', ids: ids };
  }

  function errorDetails(error) {
    return {
      name: error && typeof error.name === 'string' ? error.name : 'Error',
      message: error && typeof error.message === 'string' ? error.message : String(error)
    };
  }

  function recordError(testCase, phase, error) {
    const detail = errorDetails(error);
    testCase.errors.push({ phase: phase, name: detail.name, message: detail.message });
    return detail;
  }

  function assertEqual(actual, expected, description) {
    if (actual !== expected) {
      throw new Error(description + ': expected ' + String(expected) + ', got ' + String(actual));
    }
  }

  function propertyStore(methods) {
    if (typeof PropertiesService === 'undefined' ||
        typeof PropertiesService.getScriptProperties !== 'function') {
      throw new Error('PropertiesService.getScriptProperties is unavailable');
    }
    const store = PropertiesService.getScriptProperties();
    if (!store || methods.some(function (method) { return typeof store[method] !== 'function'; })) {
      throw new Error('Required ScriptProperties methods are unavailable');
    }
    return store;
  }

  function uuid() {
    if (typeof Utilities === 'undefined' || typeof Utilities.getUuid !== 'function') {
      throw new Error('Utilities.getUuid is unavailable');
    }
    const value = Utilities.getUuid();
    if (typeof value !== 'string' || value.length === 0) {
      throw new Error('Utilities.getUuid did not return a nonempty string');
    }
    return value;
  }

  function runPureCase(testCase) {
    let totalCents;
    try {
      totalCents = require('common-js/total-cents').totalCents;
      if (typeof totalCents !== 'function') throw new Error('totalCents fixture is unavailable');
    } catch (error) {
      testCase.outcome = 'blocked';
      recordError(testCase, 'dependency', error);
      return;
    }
    try {
      if (testCase.id === 'TC-01') {
        // Literal expectations are independent of the fixture implementation.
        [
          [0, 0, 0], [0, 199, 0], [7, 0, 0], [1, 99, 99],
          [3, 199, 597], [12, 250, 3000],
          [9007199254740991, 1, 9007199254740991],
          [9007199254740992, 1, 9007199254740992]
        ].forEach(function (example) {
          assertEqual(totalCents(example[0], example[1]), example[2], 'Exact integer-cent product');
        });
      } else {
        [undefined, null, true, false, '2', '', NaN, Infinity, -Infinity, -1, 0.5, {}, []]
          .forEach(function (invalid) {
            [0, 1].forEach(function (slot) {
              let rejected = false;
              try {
                totalCents(slot === 0 ? invalid : 2, slot === 1 ? invalid : 3);
              } catch (error) {
                rejected = true;
              }
              assertEqual(rejected, true, 'Invalid argument rejected in slot ' + slot);
            });
          });
      }
      testCase.outcome = 'passed';
    } catch (error) {
      testCase.outcome = 'failed';
      recordError(testCase, 'assertion', error);
    }
  }

  function runStatefulCase(testCase, result) {
    let store;
    let key;
    try {
      store = propertyStore(['setProperty', 'getProperty', 'deleteProperty']);
      if (result.invocationId === null) result.invocationId = uuid();
      key = PREFIX + result.invocationId + '__' + testCase.id + '__' + uuid();
      testCase.cleanup.key = key;
    } catch (error) {
      testCase.setup = 'blocked';
      testCase.outcome = 'blocked';
      recordError(testCase, 'dependency', error);
      return;
    }

    let phase = 'setup';
    try {
      store.setProperty(key, 'fixture:' + testCase.id);
      if (testCase.id === 'NC-01') throw new Error('Controlled setup failure (NC-01)');
      testCase.setup = 'passed';
      phase = 'assertion';
      assertEqual(store.getProperty(key), 'fixture:' + testCase.id, 'Fixture roundtrip');
      if (testCase.id === 'NC-02') throw new Error('Controlled assertion failure (NC-02)');
      if (testCase.id === 'TC-04') {
        store.setProperty(key, 'updated:' + testCase.id);
        assertEqual(store.getProperty(key), 'updated:' + testCase.id, 'Fixture update');
        store.deleteProperty(key);
        assertEqual(store.getProperty(key), null, 'Fixture deletion');
      }
      testCase.outcome = 'passed';
    } catch (error) {
      if (phase === 'setup') testCase.setup = 'failed';
      testCase.outcome = 'failed';
      recordError(testCase, phase, error);
    } finally {
      // Delete only this case's key, even if setup wrote and then threw.
      testCase.cleanup.attempted = true;
      try {
        store.deleteProperty(key);
        testCase.cleanup.removed = store.getProperty(key) === null;
        assertEqual(testCase.cleanup.removed, true, 'Fixture absent after teardown');
        testCase.teardown = 'passed';
      } catch (error) {
        testCase.teardown = 'failed';
        testCase.outcome = 'failed';
        testCase.cleanup.error = recordError(testCase, 'teardown', error);
      }
    }
  }

  function runRepeatableTests(selection) {
    // Reject the complete selection before any service or fixture access.
    const selected = parseSelection(selection);
    const result = {
      suiteId: 'shiploop-remote-repeatability-v1',
      sourceRevision: 'sha256:853dc9df6047c8101179f769690fe63e0cfde98aed263af0f72190b392084914',
      testDefinitionRevision: 'repeatable-tests-v1',
      invocationId: null,
      selection: selected.name,
      selectedIds: selected.ids.slice(),
      executedIds: [],
      cases: [],
      summary: { passed: 0, failed: 0, blocked: 0 },
      cleanup: { attempted: 0, removed: 0, failed: 0, unverified: 0 }
    };
    selected.ids.forEach(function (id) {
      const testCase = {
        id: id,
        outcome: 'blocked',
        setup: 'not-required',
        teardown: 'not-required',
        errors: [],
        cleanup: { key: null, attempted: false, removed: null, error: null }
      };
      result.executedIds.push(id);
      if (id === 'TC-01' || id === 'TC-02') runPureCase(testCase);
      else runStatefulCase(testCase, result);
      result.cases.push(testCase);
      result.summary[testCase.outcome] += 1;
      if (testCase.cleanup.attempted) result.cleanup.attempted += 1;
      if (testCase.cleanup.removed === true) result.cleanup.removed += 1;
      if (testCase.teardown === 'failed') result.cleanup.failed += 1;
      if (testCase.cleanup.attempted && testCase.cleanup.removed === null) result.cleanup.unverified += 1;
    });
    return result;
  }

  function inspectOwnedState() {
    const properties = propertyStore(['getProperties']).getProperties();
    if (properties === null || typeof properties !== 'object' || Array.isArray(properties)) {
      throw new Error('ScriptProperties inspection did not return a property map');
    }
    const keys = Object.keys(properties).filter(function (key) { return key.indexOf(PREFIX) === 0; }).sort();
    return { prefix: PREFIX, keys: keys, count: keys.length };
  }

  module.exports = { runRepeatableTests, inspectOwnedState };
}
__defineModule__(_main);
