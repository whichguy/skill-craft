import assert from 'node:assert/strict';
import test from 'node:test';

import * as mutant from './mutant.mjs';
import * as reference from './reference.mjs';
import * as seed from './seed.mjs';

function stateResult(implementation) {
    const prior = {
        records: [
            { id: '001', name: 'Before' },
            { id: '002', name: 'Unchanged' }
        ]
    };
    const next = implementation.replaceRecordName(prior, '001', 'After');
    return {
        rootReplaced: next !== prior,
        listReplaced: next.records !== prior.records,
        recordReplaced: next.records[0] !== prior.records[0],
        priorUnchanged: prior.records[0].name === 'Before',
        nextChanged: next.records[0].name === 'After'
    };
}

function deferred() {
    let resolve;
    const promise = new Promise((resolvePromise) => {
        resolve = resolvePromise;
    });
    return { promise, resolve };
}

async function captureInvalidation(implementation, cacheKind) {
    const gate = deferred();
    const events = [];
    const operation = implementation.commitAndInvalidate({
        cacheKind,
        wiredValue: 'wired-result',
        recordIds: ['001'],
        mutation: async () => {
            events.push('mutation:start');
            await gate.promise;
            events.push('mutation:done');
            return { id: '001' };
        },
        refreshApex: async (wiredValue) => {
            events.push(`refresh:${wiredValue}`);
        },
        notifyRecordUpdateAvailable: async (records) => {
            events.push(`notify:${JSON.stringify(records)}`);
        }
    });
    await Promise.resolve();
    const earlyEvents = [...events];
    gate.resolve();
    await operation;
    await Promise.resolve();
    return { earlyEvents, events };
}

test('reference replaces state rather than mutating the rendered identity', () => {
    assert.deepEqual(stateResult(reference), {
        rootReplaced: true,
        listReplaced: true,
        recordReplaced: true,
        priorUnchanged: true,
        nextChanged: true
    });
});

test('seed and mutant make distinct state-identity violations', () => {
    const seedResult = stateResult(seed);
    const mutantResult = stateResult(mutant);
    assert.equal(seedResult.rootReplaced, false);
    assert.equal(seedResult.priorUnchanged, false);
    assert.equal(mutantResult.rootReplaced, true);
    assert.equal(mutantResult.listReplaced, true);
    assert.equal(mutantResult.recordReplaced, false);
    assert.equal(mutantResult.priorUnchanged, false);
});

test('reference awaits mutation then refreshes only an Apex-wire cache', async () => {
    const observed = await captureInvalidation(reference, 'apex-wire');
    assert.deepEqual(observed.earlyEvents, ['mutation:start']);
    assert.deepEqual(observed.events, [
        'mutation:start',
        'mutation:done',
        'refresh:wired-result'
    ]);
});

test('reference awaits mutation then notifies only the LDS record cache', async () => {
    const observed = await captureInvalidation(reference, 'lds-record');
    assert.deepEqual(observed.earlyEvents, ['mutation:start']);
    assert.deepEqual(observed.events, [
        'mutation:start',
        'mutation:done',
        'notify:[{"recordId":"001"}]'
    ]);
});

test('seed exposes early invalidation and mutant chooses the wrong cache adapter', async () => {
    const seedObserved = await captureInvalidation(seed, 'lds-record');
    const mutantObserved = await captureInvalidation(mutant, 'apex-wire');
    assert.deepEqual(seedObserved.earlyEvents, [
        'mutation:start',
        'notify:["001"]'
    ]);
    assert.deepEqual(mutantObserved.events, [
        'mutation:start',
        'mutation:done',
        'notify:["001"]'
    ]);
});
