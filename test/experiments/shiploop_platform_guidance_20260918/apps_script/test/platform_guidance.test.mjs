import assert from "node:assert/strict";
import test from "node:test";

import {
  GridPort,
  NotificationPort,
  SyntheticQuota,
  SyntheticQuotaError,
  blindNotificationBatchMutant,
  renderCellByCellSeed,
  renderGridBatchReference,
  sendDistinctNotificationsReference,
} from "../fixtures/bulk_operations.mjs";
import {
  RpcContractError,
  createDirectCallSeed,
  createReferenceRunner,
  createReferenceRpcCall,
  createUnsafeWireMutant,
} from "../fixtures/rpc_contract.mjs";
import {
  AlwaysBusyLock,
  AsyncMutex,
  BlanketLockMutant,
  CacheAuthorityMutant,
  DurableStore,
  NoLockSeed,
  StateReference,
  VolatileCache,
  formatReadReference,
} from "../fixtures/state_transaction.mjs";

function deferred() {
  let resolve;
  const promise = new Promise(resolvePromise => {
    resolve = resolvePromise;
  });
  return {promise, resolve};
}

test("RPC reference copies legal values and rejects documented prohibited shapes", async () => {
  const input = {items: [undefined, {value: "client"}]};
  const call = createReferenceRpcCall(async payload => {
    payload.items[1].value = "server";
    return payload;
  });

  assert.deepEqual(await call(input), {
    items: [null, {value: "server"}],
  });
  assert.deepEqual(input, {items: [undefined, {value: "client"}]});

  await assert.rejects(() => call({when: new Date()}), RpcContractError);
  await assert.rejects(() => call({callback() {}}), RpcContractError);
  const circular = {};
  circular.self = circular;
  await assert.rejects(() => call(circular), RpcContractError);
});

test("RPC reference reports independent asynchronous calls through handlers", async () => {
  const events = [];
  const entered = deferred();
  const fastGate = deferred();
  const slowGate = deferred();
  const fastDelivered = deferred();
  const slowDelivered = deferred();
  let enteredCount = 0;
  const runner = createReferenceRunner({
    async complete({label}) {
      enteredCount += 1;
      if (enteredCount === 2) {
        entered.resolve();
      }
      await (label === "fast" ? fastGate.promise : slowGate.promise);
      return {label};
    },
    explode() {
      throw new Error("intentional server failure");
    },
  });

  const onSuccess = result => {
    events.push(result.label);
    if (result.label === "fast") {
      fastDelivered.resolve();
    } else {
      slowDelivered.resolve();
    }
  };
  assert.equal(runner.withSuccessHandler(onSuccess).complete({label: "slow"}), undefined);
  runner.withSuccessHandler(onSuccess).complete({label: "fast"});
  await entered.promise;
  assert.deepEqual(events, []);
  fastGate.resolve();
  await fastDelivered.promise;
  assert.deepEqual(events, ["fast"]);
  slowGate.resolve();
  await slowDelivered.promise;
  assert.deepEqual(events, ["fast", "slow"]);

  const failed = deferred();
  runner.withFailureHandler(error => failed.resolve(error.message)).explode();
  assert.equal(await failed.promise, "intentional server failure");
});

test("RPC seed and mutant fail the independent boundary probes", async () => {
  const direct = createDirectCallSeed(value => ({value}));
  assert.deepEqual(direct("immediate"), {value: "immediate"});

  const unsafe = createUnsafeWireMutant(value => value.when);
  const date = new Date("2026-09-18T00:00:00.000Z");
  assert.equal(await unsafe({when: date}), date);
});

test("state reference serializes updates and persists idempotency across cache loss", async () => {
  const store = new DurableStore();
  const service = new StateReference({
    cache: new VolatileCache(),
    lock: new AsyncMutex(),
    store,
  });

  const [first, duplicate, second] = await Promise.all([
    service.apply({delta: 1, id: "first"}),
    service.apply({delta: 1, id: "first"}),
    service.apply({delta: 1, id: "second"}),
  ]);
  assert.equal(first.value, 1);
  assert.equal(duplicate.value, 1);
  assert.equal([first.replayed, duplicate.replayed].filter(Boolean).length, 1);
  assert.equal(second.value, 2);
  assert.deepEqual(store.snapshot(), {
    commitCount: 2,
    receiptIds: ["first", "second"],
    value: 2,
  });

  const restarted = new StateReference({
    cache: new VolatileCache(),
    lock: new AsyncMutex(),
    store,
  });
  assert.equal(await restarted.readAuthoritativeValue(), 2);
  assert.deepEqual(await restarted.apply({delta: 1, id: "first"}), {
    id: "first",
    replayed: true,
    value: 1,
  });
});

test("state seed and mutants expose lost updates, volatile idempotency, and needless locking", async () => {
  const unprotectedStore = new DurableStore();
  const unprotected = new NoLockSeed({
    cache: new VolatileCache(),
    store: unprotectedStore,
  });
  await Promise.all([
    unprotected.apply({delta: 1, id: "one"}),
    unprotected.apply({delta: 1, id: "two"}),
  ]);
  assert.deepEqual(unprotectedStore.snapshot(), {
    commitCount: 2,
    receiptIds: ["one", "two"],
    value: 1,
  });

  const cacheOnlyStore = new DurableStore();
  const firstExecution = new CacheAuthorityMutant({
    cache: new VolatileCache(),
    store: cacheOnlyStore,
  });
  assert.equal((await firstExecution.apply({delta: 1, id: "once"})).replayed, false);
  const afterRestart = new CacheAuthorityMutant({
    cache: new VolatileCache(),
    store: cacheOnlyStore,
  });
  assert.equal((await afterRestart.apply({delta: 1, id: "once"})).replayed, false);
  assert.deepEqual(cacheOnlyStore.snapshot(), {
    commitCount: 0,
    receiptIds: [],
    value: 0,
  });

  assert.equal(formatReadReference("  ready  "), "READY");
  await assert.rejects(() => new BlanketLockMutant(new AlwaysBusyLock()).format("ready"), /lock unavailable/);
});

test("contiguous grid reference preserves output with one synthetic service call", () => {
  const colors = [
    ["#111", "#222"],
    ["#333", "#444"],
  ];
  const referenceQuota = new SyntheticQuota(1);
  const reference = new GridPort({columns: 2, quota: referenceQuota, rows: 2});
  renderGridBatchReference(reference, colors);
  assert.deepEqual(reference.snapshot(), colors);
  assert.equal(referenceQuota.calls, 1);

  const seed = new GridPort({columns: 2, quota: new SyntheticQuota(4), rows: 2});
  renderCellByCellSeed(seed, colors);
  assert.deepEqual(seed.snapshot(), colors);
  assert.throws(
    () => renderCellByCellSeed(new GridPort({columns: 2, quota: new SyntheticQuota(1), rows: 2}), colors),
    SyntheticQuotaError,
  );
});

test("blind batching is rejected when effects need distinct payloads", () => {
  const events = [
    {message: "approved", recipient: "owner@example.test"},
    {message: "retry needed", recipient: "operator@example.test"},
  ];
  const reference = new NotificationPort();
  sendDistinctNotificationsReference(reference, events);
  assert.deepEqual(reference.deliveries, events);

  const mutant = new NotificationPort();
  blindNotificationBatchMutant(mutant, events);
  assert.notDeepEqual(mutant.deliveries, events);
  assert.deepEqual(mutant.deliveries, [
    {message: "approved", recipient: "owner@example.test"},
    {message: "approved", recipient: "operator@example.test"},
  ]);
});
