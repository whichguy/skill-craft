'use strict';

/*
 * X8: dispatcher exact calls and dead ends. Spec:
 * test/orchestrator_scenarios/specs/dispatcher-exact-calls.md; IDs [E1]..[E7].
 * Workers are simulated; nothing launches a model.
 */

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const cli = require('./orchestrator_scenarios/dispatcher-cli');

const root = cli.makeRoot('dispatcher-exact-calls-');
const OWNER = 'parent-1';
let failures = 0;

const dispatch = (...args) => cli.dispatch(root, ...args);
const runCall = (...args) => cli.runCall(root, ...args);
const evidence = (value) => cli.evidence(root, value);

function newRun(steps, extra = {}) {
  const run = path.join(root, 'runs', crypto.randomUUID());
  fs.mkdirSync(path.dirname(run), { recursive: true });
  dispatch('init', run, { owner: OWNER, graph: cli.graphOf(steps), ...extra });
  return run;
}

function contextValues(step, attempt) {
  const workspace = path.join(root, 'ws', attempt);
  fs.mkdirSync(workspace, { recursive: true });
  return { workspace, write_scope: ['src/' + step + '.json'], ready_evidence: evidence({ step, attempt }) };
}

// The simulated native worker: writes its result and runs the packet's report_argv.
function work(packet, status = 'SUCCEEDED') {
  fs.writeFileSync(packet.outputs.artifact, JSON.stringify({ step: packet.step, attempt: packet.attempt, status }));
  const envelope = {
    ...packet.report_envelope, status,
    evidence: { path: packet.outputs.artifact, sha256: cli.digest(fs.readFileSync(packet.outputs.artifact)) },
  };
  fs.writeFileSync(packet.outputs.envelope, JSON.stringify(envelope));
  return cli.argvRun(packet.report_argv);
}

function verification(passed) {
  return { passed, reason: passed ? 'independent check passed' : 'independent check failed',
    evidence: evidence({ passed }) };
}

// Drive one step through the returned calls only: claim -> start -> launched -> work -> settle.
function runStepByCalls(run, step, status = 'SUCCEEDED') {
  const view = dispatch('next', run);
  const claimAction = view.actions.find((item) => item.action === 'claim');
  assert.ok(claimAction && claimAction.call, 'claim action carries a call');
  const claimed = runCall({ ...claimAction.call, input: { ...claimAction.call.input, steps: [step] } });
  const entry = claimed.calls.find((item) => item.step === step);
  const started = runCall(entry.call, contextValues(step, entry.attempt));
  assert.equal(started.call.argv[2], 'launched');
  runCall(started.call, { handle: 'SIMULATED-' + entry.attempt });
  work(started.packet, status);
  const verify = dispatch('next', run).actions.find((item) => item.action === 'verify' && item.step === step);
  assert.match(verify.call.input.verification.receipt_sha256, /^[0-9a-f]{64}$/);
  return { attempt: entry.attempt, settled: runCall(verify.call, verification(status === 'SUCCEEDED')) };
}

async function test(name, fn) {
  try {
    await fn();
    console.log('PASS ' + name);
  } catch (error) {
    failures += 1;
    console.log('FAIL ' + name + '\n' + (error.stack || error));
  }
}

async function main() {
  await test('[E1][E2] a chain completes using only returned calls; completion returns no next call', () => {
    const run = newRun([['A', []], ['B', ['A']], ['C', ['B']]]);
    let response = cli.argvRun([process.execPath, cli.helper, 'next', run]);
    const seen = new Set();
    for (let guard = 0; guard < 40 && !response.complete; guard += 1) {
      for (const action of response.actions) {
        assert.ok(action.call || action.calls, 'action ' + action.action + ' carries a call');
        seen.add(action.action);
      }
      const action = response.actions[0];
      if (action.action === 'claim') {
        const claimed = runCall(action.call);
        for (const entry of claimed.calls) {
          const started = runCall(entry.call, contextValues(entry.step, entry.attempt));
          runCall(started.call, { handle: 'SIMULATED-' + entry.attempt });
          work(started.packet);
        }
        response = cli.argvRun(claimed.next_argv);
      } else if (action.action === 'verify') {
        assert.match(action.call.input.verification.receipt_sha256, /^[0-9a-f]{64}$/);
        response = runCall(action.call, verification(true));
      } else {
        response = runCall(action.call);
      }
    }
    assert.equal(response.complete, true);
    assert.deepEqual([...seen].sort(), ['claim', 'verify']);
    assert.equal(Object.hasOwn(response, 'next_argv'), false, 'a complete response has no next_argv');
    const again = dispatch('next', run);
    assert.equal(again.complete, true);
    assert.equal(Object.hasOwn(again, 'next_argv'), false);
  });

  await test('[E3] deleting a rejected attempt\'s workspace and evidence does not brick the run', () => {
    const run = newRun([['A', []], ['B', ['A']]]);
    const { attempt } = runStepByCalls(run, 'A', 'FAILED');
    const context = dispatch('packet', run, { attempt }).packet.context;
    fs.rmSync(context.workspace, { recursive: true, force: true });
    fs.rmSync(context.ready_evidence.path, { force: true });
    dispatch('next', run);
    dispatch('takeover', run, { oldOwner: OWNER, newOwner: 'parent-2', confirmed_stopped: true, reason: 'handoff' });
    const retry = dispatch('next', run).actions.find((item) => item.action === 'retry');
    assert.equal(retry.call.input.owner, 'parent-2');
    runCall(retry.call, { reason: 'fresh fixture' });
    const view = dispatch('next', run);
    const claimAction = view.actions.find((item) => item.action === 'claim');
    assert.deepEqual(claimAction.steps, ['A']);
  });

  await test('[E4] concurrent claims wait for the lock instead of failing', async () => {
    const ids = Array.from({ length: 20 }, (_, index) => 'S' + index);
    const run = newRun(ids.map((id) => [id, []]));
    const results = await Promise.all(ids.map((id) => cli.runAsync(
      [process.execPath, cli.helper, 'claim', run, cli.saveJson(root, { owner: OWNER, steps: [id] })])));
    const locked = results.filter((result) => result.stderr.includes('ELOCKED'));
    assert.equal(locked.length, 0, locked.length + ' claims failed with ELOCKED');
    assert.equal(results.filter((result) => result.status === 0).length, 20);
    assert.equal(dispatch('next', run).active.length, 20);
  });

  await test('[E5] capacity limits offers and claims, refills after a settle, and must be a positive integer', () => {
    const ids = Array.from({ length: 10 }, (_, index) => 'S' + index);
    for (const bad of [0, -1, 1.5, '3']) {
      const run = path.join(root, 'runs', crypto.randomUUID());
      const error = dispatch('init', run, { owner: OWNER, graph: cli.graphOf(ids.map((id) => [id, []])), capacity: bad }, true);
      assert.match(error.error, /capacity/);
    }
    const run = newRun(ids.map((id) => [id, []]), { capacity: 3 });
    let claimAction = dispatch('next', run).actions.find((item) => item.action === 'claim');
    assert.deepEqual(claimAction.steps, ['S0', 'S1', 'S2']);
    assert.deepEqual(claimAction.call.input.steps, ['S0', 'S1', 'S2']);
    const claimed = runCall(claimAction.call);
    assert.equal(dispatch('next', run).actions.some((item) => item.action === 'claim'), false);
    const refused = dispatch('claim', run, { owner: OWNER, steps: ['S3'] }, true);
    assert.equal(refused.code, 'ECAPACITY');
    const entry = claimed.calls[0];
    const started = runCall(entry.call, contextValues(entry.step, entry.attempt));
    runCall(started.call, { handle: 'SIMULATED-' + entry.attempt });
    work(started.packet);
    const verify = dispatch('next', run).actions.find((item) => item.action === 'verify');
    runCall(verify.call, verification(true));
    claimAction = dispatch('next', run).actions.find((item) => item.action === 'claim');
    assert.deepEqual(claimAction.steps, ['S3']);
  });

  await test('[E6] a planning-blocked step is not offered for claim and cannot be claimed', () => {
    const save = (value, ext = '.json') => {
      const file = path.join(root, 'files', crypto.randomUUID() + ext);
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value));
      return file;
    };
    const reference = (file) => ({ path: file, sha256: cli.digest(fs.readFileSync(file)) });
    const graph = cli.graphOf([['B', []], ['C', []]]);
    const brief = save('# brief\n', '.md');
    const bMaterial = save('B planning material\n', '.md');
    const manifest = {
      schema: 'shiploop-planning-artifacts/v1',
      source: { run_id: 'r', action_id: 'a', workitem: 'w', revision: 1 },
      graph: reference(save(graph)),
      briefing: reference(brief),
      artifacts: [
        { ...reference(brief), roles: ['planning-brief'], producers: ['planning-context'], classification: 'current', required_for: ['*'] },
        { ...reference(bMaterial), roles: ['requirements'], producers: ['spec-1'], classification: 'current', required_for: ['B'] },
      ],
      unresolved_refs: [],
      reference_only: [],
    };
    const run = path.join(root, 'runs', crypto.randomUUID());
    dispatch('init', run, { owner: OWNER, graph, planning_context: { ...reference(save(manifest)), source: { run_id: 'r', action_id: 'a' } } });
    fs.writeFileSync(bMaterial, 'CHANGED B planning material\n');
    const view = dispatch('next', run);
    assert.deepEqual(view.planning_blocked_steps, ['B']);
    const claimAction = view.actions.find((item) => item.action === 'claim');
    assert.deepEqual(claimAction.steps, ['C']);
    const refused = dispatch('claim', run, { owner: OWNER, steps: ['B'] }, true);
    assert.equal(refused.code, 'EPLANNING_CONTEXT');
  });

  await test('[E7] without capacity every ready step is offered and claimable', () => {
    const ids = Array.from({ length: 10 }, (_, index) => 'S' + index);
    const run = newRun(ids.map((id) => [id, []]));
    const claimAction = dispatch('next', run).actions.find((item) => item.action === 'claim');
    assert.deepEqual(claimAction.steps, ids);
    assert.equal(runCall(claimAction.call).claims.length, 10);
  });

  if (failures) {
    console.log(failures + ' failed; fixture root retained: ' + root);
    process.exitCode = 1;
  } else {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

main();
