'use strict';

/*
 * Bounded compounded-dispatch regression.  This uses the real durable
 * dispatcher package copied into a cold location.  The "native workers" below
 * are deliberately simulated fixtures: they only write result files and call
 * the public report command; they never launch a model or agent.
 *
 * CALLER_NATIVE_CAPACITY is a policy enforced by this test's caller.  The
 * durable engine records explicit claims and reservations, but it is not an
 * automatic global worker scheduler and must keep deferred ready work visible.
 */

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const repo = path.resolve(__dirname, '..');
const state = require(path.join(repo, 'skills/plan-dispatcher/scripts/state.js'));
const CALLER_NATIVE_CAPACITY = 3;
const STATE_FILE = 'plan-dispatcher-state.json';
const SEEDED_RUNS = [10, 21, 34, 55];
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'backchain-dispatcher-compound-')));
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const observations = [];

function saveJson(value, destination) {
  const target = destination || path.join(root, 'files', crypto.randomUUID() + '.json');
  fs.mkdirSync(path.dirname(target), { recursive: true });
  if (destination) {
    fs.writeFileSync(target, JSON.stringify(value));
  } else {
    fs.writeFileSync(target, JSON.stringify(value), { flag: 'wx' });
  }
  return target;
}

function evidence(value) {
  const file = saveJson(value);
  return { path: file, sha256: digest(fs.readFileSync(file)) };
}

function contract(id) {
  return {
    task: 'Simulated durable task ' + id,
    ready: ['Inputs for ' + id + ' independently checked'],
    done: [id + ' result independently verified'],
  };
}

function compoundGraph() {
  const step = (id, deps) => ({ id, deps, contract: contract(id) });
  return {
    version: 1,
    steps: [
      step('ROOT', []),
      step('SLOW', []),
      step('B', ['ROOT']),
      step('C', ['ROOT']),
      step('D', ['ROOT']),
      step('E', ['ROOT']),
      step('F', ['B']),
      step('G', ['B']),
      step('H', ['C']),
      step('I', ['C']),
      step('K', ['D']),
      step('L', ['E']),
      step('JOIN', ['F', 'G', 'H', 'I', 'K', 'L', 'SLOW']),
    ],
  };
}

function makeContext(step, attempt, resources = []) {
  const workspace = path.join(root, 'workspaces', step + '-' + attempt);
  fs.mkdirSync(workspace, { recursive: true });
  return {
    workspace,
    write_scope: ['src/' + step.toLowerCase() + '.json'],
    resources,
    ready_evidence: evidence({
      fixture: 'SIMULATED_NATIVE_WORKER readiness',
      step,
      attempt,
      resources,
    }),
  };
}

function parseError(stderr) {
  try {
    return JSON.parse(stderr);
  } catch (_) {
    return { error: stderr };
  }
}

function copiedCli(helper, unrelated, operation, run, input, expectFailure = false) {
  let inputFile;
  if (input !== undefined) {
    inputFile = operation === 'report'
      ? path.join(run, 'artifacts', input.attempt, 'envelope.json')
      : saveJson(input);
    if (operation === 'report') {
      saveJson(input, inputFile);
    }
  }
  const child = spawnSync(
    process.execPath,
    [helper, operation, run, ...(inputFile === undefined ? [] : [inputFile])],
    { cwd: unrelated, encoding: 'utf8', timeout: 8000 }
  );
  assert.ifError(child.error);
  if (expectFailure) {
    assert.notEqual(child.status, 0, operation + ' unexpectedly succeeded');
    return parseError(child.stderr);
  }
  assert.equal(child.status, 0, operation + ': ' + child.stderr);
  assert.equal(child.stderr, '');
  return JSON.parse(child.stdout);
}

function coldNext(helper, unrelated, run) {
  return copiedCli(helper, unrelated, 'next', run);
}

function assertDeferredReady(helper, unrelated, run, expected) {
  const view = coldNext(helper, unrelated, run);
  assert.deepEqual(view.ready, expected);
  const action = view.actions.find((item) => item.action === 'claim');
  if (expected.length === 0) {
    assert.equal(action, undefined);
  } else {
    assert.ok(action, 'cold next must advertise every deferred ready step');
    assert.deepEqual(action.steps, expected);
  }
  return view;
}

function claimWithinCallerCapacity(helper, unrelated, run, owner, steps) {
  const view = coldNext(helper, unrelated, run);
  const available = CALLER_NATIVE_CAPACITY - view.active.length;
  if (steps.length > available) {
    throw new Error('caller capacity exceeded: requested ' + steps.length + ', available ' + available);
  }
  for (const step of steps) {
    if (!view.ready.includes(step)) {
      throw new Error('caller policy cannot claim nonready or omitted step: ' + step);
    }
  }
  return copiedCli(helper, unrelated, 'claim', run, { owner, steps });
}

function launchSimulatedNative(helper, unrelated, run, owner, claim, resources = []) {
  const context = makeContext(claim.step, claim.attempt, resources);
  const started = copiedCli(helper, unrelated, 'start', run, {
    owner,
    attempt: claim.attempt,
    context,
  });
  assert.equal(started.action, 'launch');
  const launched = copiedCli(helper, unrelated, 'launched', run, {
    owner,
    attempt: claim.attempt,
    handle: 'SIMULATED_NATIVE_WORKER-' + claim.step + '-' + claim.attempt,
  });
  assert.equal(launched.status, 'running');
  return { claim, context, started };
}

function publishSimulatedNative(helper, unrelated, run, native, status = 'SUCCEEDED') {
  const artifact = native.started.packet.outputs.artifact;
  fs.writeFileSync(artifact, JSON.stringify({
    fixture: 'SIMULATED_NATIVE_WORKER completion',
    step: native.claim.step,
    attempt: native.claim.attempt,
    status,
  }));
  const envelope = {
    run_id: native.started.run_id,
    step: native.claim.step,
    attempt: native.claim.attempt,
    status,
    evidence: { path: artifact, sha256: digest(fs.readFileSync(artifact)) },
  };
  const reported = copiedCli(helper, unrelated, 'report', run, envelope);
  const receipt = copiedCli(helper, unrelated, 'receipt', run, { attempt: native.claim.attempt });
  // Continuation metadata is not part of the durable, digest-bound receipt.
  assert.deepEqual(
    { envelope: receipt.envelope, sha256: receipt.sha256 },
    { envelope: reported.envelope, sha256: reported.sha256 }
  );
  assert.deepEqual(reported.next_argv, [process.execPath, helper, 'next', run]);
  assert.deepEqual(receipt.next_argv, reported.next_argv);
  assert.deepEqual(receipt.envelope, envelope);
  return { ...native, envelope, receipt };
}

function settleSimulatedNative(helper, unrelated, run, owner, published, passed = true) {
  const artifactBytes = fs.readFileSync(published.envelope.evidence.path);
  assert.equal(digest(artifactBytes), published.envelope.evidence.sha256);
  const verification = {
    receipt_sha256: published.receipt.sha256,
    passed,
    reason: passed
      ? 'SIMULATED independent completion and done verification passed'
      : 'SIMULATED independent completion verifier rejected this result',
    evidence: evidence({
      fixture: 'SIMULATED_INDEPENDENT_VERIFIER',
      step: published.claim.step,
      attempt: published.claim.attempt,
      passed,
      artifact_sha256: published.envelope.evidence.sha256,
    }),
  };
  const settled = copiedCli(helper, unrelated, 'settle', run, {
    owner,
    attempt: published.claim.attempt,
    verification,
  });
  return { ...published, verification, settled };
}

function completeSimulatedNative(helper, unrelated, run, owner, claim, resources = []) {
  return settleSimulatedNative(
    helper,
    unrelated,
    run,
    owner,
    publishSimulatedNative(helper, unrelated, run, launchSimulatedNative(helper, unrelated, run, owner, claim, resources))
  );
}

function test(name, fn) {
  const began = Date.now();
  const detail = fn();
  observations.push({ name, duration_ms: Date.now() - began, ...(detail || {}) });
  console.log('PASS ' + name);
}

function seededGraph(seed) {
  const width = 3 + (seed & 1);
  const rootId = 'R' + seed;
  const layerOne = Array.from({ length: width }, (_, index) => 'A' + seed + '_' + index);
  const layerTwo = Array.from({ length: width }, (_, index) => 'B' + seed + '_' + index);
  const layerThree = ['C' + seed + '_0', 'C' + seed + '_1'];
  const steps = [{ id: rootId, deps: [], contract: contract(rootId) }];
  for (const id of layerOne) {
    steps.push({ id, deps: [rootId], contract: contract(id) });
  }
  for (let index = 0; index < width; index += 1) {
    const id = layerTwo[index];
    steps.push({
      id,
      deps: [layerOne[index], layerOne[(index + 1) % width]],
      contract: contract(id),
    });
  }
  steps.push({ id: layerThree[0], deps: [layerTwo[0], layerTwo[1]], contract: contract(layerThree[0]) });
  steps.push({
    id: layerThree[1],
    deps: [layerTwo[width - 2], layerTwo[width - 1]],
    contract: contract(layerThree[1]),
  });
  const joinId = 'J' + seed;
  steps.push({ id: joinId, deps: layerThree, contract: contract(joinId) });
  return { version: 1, steps };
}

// This intentionally only evaluates graph edges and the accepted set.  It
// does not inspect the implementation's status records or reuse its helpers.
function referenceReady(graph, accepted) {
  return graph.steps
    .filter((step) => !accepted.has(step.id) && step.deps.every((dependency) => accepted.has(dependency)))
    .map((step) => step.id);
}

function directCompleteSeeded(run, owner, claim) {
  const context = makeContext(claim.step, claim.attempt);
  assert.equal(state.start(run, owner, claim.attempt, context).action, 'launch');
  state.launched(run, owner, claim.attempt, 'SIMULATED_NATIVE_WORKER-' + claim.attempt);
  const envelope = {
    run_id: claim.run_id,
    step: claim.step,
    attempt: claim.attempt,
    status: 'SUCCEEDED',
    evidence: evidence({ fixture: 'SIMULATED_NATIVE_WORKER seeded result', step: claim.step }),
  };
  state.report(run, envelope);
  const receipt = state.receipt(run, claim.attempt);
  const settled = state.settle(run, owner, claim.attempt, {
    receipt_sha256: receipt.sha256,
    passed: true,
    reason: 'SIMULATED seeded independent verification passed',
    evidence: evidence({ fixture: 'SIMULATED_INDEPENDENT_VERIFIER', step: claim.step }),
  });
  assert.equal(settled.outcome, 'accepted');
}

function runSeededReadinessOrder(seed) {
  const graph = seededGraph(seed);
  assert.ok(graph.steps.length >= 10 && graph.steps.length <= 20);
  const run = path.join(root, 'seeded-runs', String(seed));
  const owner = 'seed-owner-' + seed;
  fs.mkdirSync(path.dirname(run), { recursive: true });
  state.init(run, graph, owner);
  const accepted = new Set();
  let entropy = seed >>> 0;
  const completionOrder = [];
  while (accepted.size < graph.steps.length) {
    const expected = referenceReady(graph, accepted);
    assert.deepEqual(state.inspect(run).ready, expected, 'seed ' + seed + ' readiness diverged from independent model');
    assert.ok(expected.length > 0, 'seed ' + seed + ' must retain a ready step until complete');
    entropy = (Math.imul(entropy, 1664525) + 1013904223) >>> 0;
    const selected = expected[entropy % expected.length];
    const claim = state.claim(run, owner, 1, [selected]).claims[0];
    directCompleteSeeded(run, owner, claim);
    accepted.add(selected);
    completionOrder.push(selected);
  }
  assert.equal(state.inspect(run).complete, true);
  return { seed, steps: graph.steps.length, completion_order_length: completionOrder.length };
}

try {
  const copied = path.join(root, 'copied-skill');
  const unrelated = path.join(root, 'unrelated-cwd');
  fs.cpSync(path.join(repo, 'skills/plan-dispatcher'), copied, { recursive: true });
  fs.mkdirSync(unrelated);
  const helper = path.join(copied, 'scripts/dispatch.js');

  test('compounded caller policy preserves durable scheduler boundaries', () => {
    const ownerOne = 'caller-one';
    const ownerTwo = 'caller-two';
    const run = path.join(root, 'compound-run');
    const initialized = copiedCli(helper, unrelated, 'init', run, { graph: compoundGraph(), owner: ownerOne });
    assert.deepEqual(initialized.ready, ['ROOT', 'SLOW']);

    // The slow branch remains independent and unfinished while the ROOT
    // cascade proceeds.  It occupies one caller-managed worker slot.
    const slow = claimWithinCallerCapacity(helper, unrelated, run, ownerOne, ['SLOW']).claims[0];
    const slowNative = launchSimulatedNative(helper, unrelated, run, ownerOne, slow, ['slow-branch']);
    const rootClaim = claimWithinCallerCapacity(helper, unrelated, run, ownerOne, ['ROOT']).claims[0];
    const rootNative = launchSimulatedNative(helper, unrelated, run, ownerOne, rootClaim, ['root-branch']);
    assert.match(
      copiedCli(helper, unrelated, 'claim', run, { owner: ownerOne, steps: ['B'] }, true).error,
      /nonready|accepted|dependenc/i
    );
    const rootPublished = publishSimulatedNative(helper, unrelated, run, rootNative);

    // A reported receipt is only a handoff: dependencies cannot be claimed
    // before an independent verifier settles the exact receipt.
    assertDeferredReady(helper, unrelated, run, []);
    assert.match(
      copiedCli(helper, unrelated, 'claim', run, { owner: ownerOne, steps: ['B'] }, true).error,
      /nonready|accepted|dependenc/i
    );
    const rootDone = settleSimulatedNative(helper, unrelated, run, ownerOne, rootPublished);
    assert.equal(rootDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['B', 'C', 'D', 'E']);

    // Four candidates are deliberately wider than the caller's two free
    // slots.  The engine advertises all four; this caller chooses B and C.
    const firstFrontier = claimWithinCallerCapacity(helper, unrelated, run, ownerOne, ['B', 'C']).claims;
    const bFirst = firstFrontier.find((claim) => claim.step === 'B');
    const c = firstFrontier.find((claim) => claim.step === 'C');
    const bFirstNative = launchSimulatedNative(helper, unrelated, run, ownerOne, bFirst, ['branch-b-first']);
    const cNative = launchSimulatedNative(helper, unrelated, run, ownerOne, c, ['branch-c']);
    assert.throws(
      () => claimWithinCallerCapacity(helper, unrelated, run, ownerOne, ['D']),
      /caller capacity exceeded/
    );
    assertDeferredReady(helper, unrelated, run, ['D', 'E']);

    // B produces a success receipt that the independent verifier rejects.
    // Its descendants block until a fresh, confirmed-stopped retry succeeds.
    const bRejected = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerOne,
      publishSimulatedNative(helper, unrelated, run, bFirstNative),
      false
    );
    assert.equal(bRejected.settled.outcome, 'rejected');
    assertDeferredReady(helper, unrelated, run, ['D', 'E']);
    const oldReceipt = copiedCli(helper, unrelated, 'receipt', run, { attempt: bFirst.attempt });
    assert.deepEqual(oldReceipt, bRejected.receipt);

    // The old caller is fenced before retry.  The old immutable receipt stays
    // readable but cannot be replayed for the replacement attempt.
    const takeover = copiedCli(helper, unrelated, 'takeover', run, {
      oldOwner: ownerOne,
      newOwner: ownerTwo,
      confirmed_stopped: true,
      reason: 'SIMULATED previous dispatcher process stopped before takeover',
    });
    assert.equal(takeover.owner, ownerTwo);
    assert.match(
      copiedCli(helper, unrelated, 'retry', run, {
        owner: ownerOne,
        attempt: bFirst.attempt,
        confirmed_stopped: true,
        reason: 'SIMULATED stale caller retry',
      }, true).error,
      /owner.*dispatcher|does not hold/i
    );
    assert.match(
      copiedCli(helper, unrelated, 'claim', run, { owner: ownerOne, steps: ['D'] }, true).error,
      /owner.*dispatcher|does not hold/i
    );
    copiedCli(helper, unrelated, 'retry', run, {
      owner: ownerTwo,
      attempt: bFirst.attempt,
      confirmed_stopped: true,
      reason: 'SIMULATED rejected worker is confirmed stopped',
    });
    assert.match(copiedCli(helper, unrelated, 'report', run, bRejected.envelope, true).error, /stale/i);
    assert.match(
      copiedCli(helper, unrelated, 'settle', run, {
        owner: ownerTwo,
        attempt: bFirst.attempt,
        verification: bRejected.verification,
      }, true).error,
      /stale/i
    );
    assertDeferredReady(helper, unrelated, run, ['B', 'D', 'E']);

    const bRetry = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['B']).claims[0];
    const bRetryNative = launchSimulatedNative(helper, unrelated, run, ownerTwo, bRetry, ['branch-b-retry']);
    const cDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, cNative)
    );
    assert.equal(cDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['D', 'E', 'H', 'I']);

    const d = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['D']).claims[0];
    const dNative = launchSimulatedNative(helper, unrelated, run, ownerTwo, d, ['shared-release-lock']);
    const bDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, bRetryNative)
    );
    assert.equal(bDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['E', 'F', 'G', 'H', 'I']);

    // E is claimed within capacity, but D's live reservation blocks a shared
    // resource start.  The failed start leaves E claimed and all other ready
    // work visible; the caller must choose a non-conflicting context.
    const e = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['E']).claims[0];
    const beforeSharedStart = fs.readFileSync(path.join(run, STATE_FILE));
    assert.match(
      copiedCli(helper, unrelated, 'start', run, {
        owner: ownerTwo,
        attempt: e.attempt,
        context: makeContext(e.step, e.attempt + '-shared', ['shared-release-lock']),
      }, true).error,
      /resource|reserved|conflict/i
    );
    assert.deepEqual(fs.readFileSync(path.join(run, STATE_FILE)), beforeSharedStart);
    assertDeferredReady(helper, unrelated, run, ['F', 'G', 'H', 'I']);
    assert.throws(
      () => claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['F']),
      /caller capacity exceeded/
    );
    const eNative = launchSimulatedNative(helper, unrelated, run, ownerTwo, e, ['isolated-release-lock']);
    const eDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, eNative)
    );
    assert.equal(eDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['F', 'G', 'H', 'I', 'L']);

    const f = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['F']).claims[0];
    const fDone = completeSimulatedNative(helper, unrelated, run, ownerTwo, f, ['branch-f']);
    assert.equal(fDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['G', 'H', 'I', 'L']);
    const g = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['G']).claims[0];
    const gDone = completeSimulatedNative(helper, unrelated, run, ownerTwo, g, ['branch-g']);
    assert.equal(gDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['H', 'I', 'L']);
    const h = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['H']).claims[0];
    const hDone = completeSimulatedNative(helper, unrelated, run, ownerTwo, h, ['branch-h']);
    assert.equal(hDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['I', 'L']);

    const dDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, dNative)
    );
    assert.equal(dDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['I', 'K', 'L']);
    const iAndK = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['I', 'K']).claims;
    const i = iAndK.find((claim) => claim.step === 'I');
    const k = iAndK.find((claim) => claim.step === 'K');
    const iNative = launchSimulatedNative(helper, unrelated, run, ownerTwo, i, ['branch-i']);
    const kNative = launchSimulatedNative(helper, unrelated, run, ownerTwo, k, ['branch-k']);
    const kDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, kNative)
    );
    assert.equal(kDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['L']);
    const l = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['L']).claims[0];
    const lDone = completeSimulatedNative(helper, unrelated, run, ownerTwo, l, ['branch-l']);
    assert.equal(lDone.settled.outcome, 'accepted');
    const iDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, iNative)
    );
    assert.equal(iDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, []);

    const slowDone = settleSimulatedNative(
      helper,
      unrelated,
      run,
      ownerTwo,
      publishSimulatedNative(helper, unrelated, run, slowNative)
    );
    assert.equal(slowDone.settled.outcome, 'accepted');
    assertDeferredReady(helper, unrelated, run, ['JOIN']);

    const join = claimWithinCallerCapacity(helper, unrelated, run, ownerTwo, ['JOIN']).claims[0];
    const coldPacket = copiedCli(helper, unrelated, 'packet', run, { attempt: join.attempt }).packet;
    assert.equal(coldPacket.helper, helper);
    const supplierOutcomes = new Map([
      ['F', fDone], ['G', gDone], ['H', hDone], ['I', iDone], ['K', kDone], ['L', lDone], ['SLOW', slowDone],
    ]);
    assert.deepEqual(coldPacket.dependencies.map((dependency) => dependency.step), ['F', 'G', 'H', 'I', 'K', 'L', 'SLOW']);
    for (const dependency of coldPacket.dependencies) {
      const supplier = supplierOutcomes.get(dependency.step);
      assert.ok(supplier, 'final packet includes only expected accepted suppliers');
      assert.deepEqual(dependency.result, supplier.envelope.evidence);
      assert.deepEqual(dependency.verification, supplier.verification.evidence);
      assert.equal(dependency.receipt_sha256, supplier.receipt.sha256);
    }
    const joinDone = completeSimulatedNative(helper, unrelated, run, ownerTwo, join, ['final-join']);
    assert.equal(joinDone.settled.complete, true);
    assert.equal(coldNext(helper, unrelated, run).complete, true);
  });

  test('seeded independent readiness oracle covers varied widths, depths, and joins', () => {
    const summaries = SEEDED_RUNS.map(runSeededReadinessOrder);
    assert.deepEqual(summaries.map((summary) => summary.steps), [10, 12, 10, 12]);
    return { seeded: summaries };
  });

  console.log(JSON.stringify({
    suite: 'plan-dispatcher-compound.test.js',
    groups_passed: observations.length,
    caller_capacity_policy: CALLER_NATIVE_CAPACITY,
    main_stress_graph_steps: compoundGraph().steps.length,
    seeded_reference_runs: SEEDED_RUNS,
    seeded_reference_step_counts: [10, 12, 10, 12],
    total_seeded_completions: 44,
    simulated_native_workers_only: true,
    observations,
  }));
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
