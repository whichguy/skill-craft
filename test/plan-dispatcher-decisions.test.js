'use strict';

/*
 * Dispatcher decisions D2-D5 (docs/plan-orchestrator-validation-plan-2026-09-27.md).
 * Spec, review and adversarial table: test/orchestrator_scenarios/specs/dispatcher-decisions.md.
 * Scenario IDs [S1]..[S14] match that spec. Workers are simulated: they write a
 * result file and call the public report command; nothing launches a model.
 *
 * PLAN_DISPATCHER_DIR selects the package under test so
 * test/orchestrator_scenarios/mutate.py can run this suite against mutants.
 */

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const cli = require('./orchestrator_scenarios/dispatcher-cli');

// PLAN_DISPATCHER_DIR (read by dispatcher-cli) selects the package under test.
const statePath = path.join(cli.pkg, 'scripts/state.js');
const root = cli.makeRoot('dispatcher-decisions-');
const OWNER = 'parent-1';
let failures = 0;

const saveJson = (value, target) => cli.saveJson(root, value, target);
const evidence = (value) => cli.evidence(root, value);
const argvRun = cli.argvRun;
const digest = cli.digest;
const dispatch = (...args) => cli.dispatch(root, ...args);
const contract = cli.contract;

function parseError(stderr) {
  try {
    return JSON.parse(stderr);
  } catch (_) {
    return { error: stderr, code: 'UNPARSED' };
  }
}

// Run a returned recovery call exactly, filling only its reason placeholder.
function runCall(call, reason, expectFailure = false) {
  assert.match(call.input.reason, /^<.*>$/, 'reason must be a placeholder for the caller');
  return cli.runCall(root, call, { reason }, expectFailure);
}

function newRun(steps) {
  const run = path.join(root, 'runs', crypto.randomUUID());
  fs.mkdirSync(path.dirname(run), { recursive: true });
  const graph = { version: 1, steps: steps.map(([id, deps]) => ({ id, deps, contract: contract(id) })) };
  dispatch('init', run, { owner: OWNER, graph });
  return run;
}

// Deep chain A->B->C->D plus an independent E->F.
const DEEP = [['A', []], ['B', ['A']], ['C', ['B']], ['D', ['C']], ['E', []], ['F', ['E']]];

function claimOne(run, step) {
  const claimed = dispatch('claim', run, { owner: OWNER, steps: [step] });
  const packet = claimed.claims.find((item) => item.step === step);
  assert.ok(packet, 'claim returned no packet for ' + step);
  return packet.attempt;
}

function launch(run, step, attempt) {
  const workspace = path.join(root, 'ws', attempt);
  fs.mkdirSync(workspace, { recursive: true });
  const started = dispatch('start', run, {
    owner: OWNER, attempt,
    context: { workspace, write_scope: ['src/' + step + '.json'], resources: [], ready_evidence: evidence({ step, attempt }) },
  });
  assert.equal(started.action, 'launch');
  dispatch('launched', run, { owner: OWNER, attempt, handle: 'SIMULATED-' + attempt });
  return started;
}

function reportAndSettle(run, step, attempt, started, status, verificationExtra, expectFailure = false) {
  const artifact = started.packet.outputs.artifact;
  fs.writeFileSync(artifact, JSON.stringify({ step, attempt, status }));
  const envelope = {
    run_id: started.run_id, step, attempt, status,
    evidence: { path: artifact, sha256: digest(fs.readFileSync(artifact)) },
  };
  dispatch('report', run, envelope);
  const receipt = dispatch('receipt', run, { attempt });
  const verification = {
    receipt_sha256: receipt.sha256,
    passed: status === 'SUCCEEDED',
    reason: status === 'SUCCEEDED' ? 'independent check passed' : step + ' independently confirmed ' + status,
    evidence: evidence({ step, attempt, status }),
    ...verificationExtra,
  };
  return { verification, result: dispatch('settle', run, { owner: OWNER, attempt, verification }, expectFailure) };
}

function runStep(run, step, status = 'SUCCEEDED', extra = {}) {
  const attempt = claimOne(run, step);
  const started = launch(run, step, attempt);
  return { attempt, ...reportAndSettle(run, step, attempt, started, status, extra) };
}

function rows(view, group) {
  return view.progress[group].map((row) => row.step);
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

// ---- D2: lock recovery (public CLI; S6 drives state.js in a child process) ----

function deadPid() {
  const child = spawnSync(process.execPath, ['-e', 'process.stdout.write(String(process.pid))'], { encoding: 'utf8' });
  return Number(child.stdout);
}

function stateClaim(run, expectFailure = false) {
  return dispatch('claim', run, { owner: OWNER, steps: ['A'] }, expectFailure);
}

function lockRun() {
  const run = newRun([['A', []]]);
  return { run, lock: path.join(run, '.dispatcher.lock'), guard: path.join(run, '.dispatcher.lock.recover') };
}

async function main() {
  await test('[S1] a dead local holder is recovered and no lock or guard remains', () => {
    const { run, lock, guard } = lockRun();
    fs.writeFileSync(lock, JSON.stringify({ pid: deadPid(), host: os.hostname() }));
    const claimed = stateClaim(run);
    assert.equal(claimed.claims.length, 1);
    assert.equal(fs.existsSync(lock), false);
    assert.equal(fs.existsSync(guard), false);
  });

  await test('[S2] a live local holder is refused and its lock is untouched', () => {
    const { run, lock } = lockRun();
    const bytes = JSON.stringify({ pid: process.pid, host: os.hostname() });
    fs.writeFileSync(lock, bytes);
    const error = stateClaim(run, true);
    assert.equal(error.code, 'ELOCKED');
    assert.match(error.error, new RegExp('running pid ' + process.pid));
    assert.equal(fs.readFileSync(lock, 'utf8'), bytes);
  });

  await test('[S3] a holder on another host is refused even when its pid is dead here', () => {
    const { run, lock } = lockRun();
    const bytes = JSON.stringify({ pid: deadPid(), host: 'elsewhere.invalid' });
    fs.writeFileSync(lock, bytes);
    const error = stateClaim(run, true);
    assert.equal(error.code, 'ELOCKED');
    assert.match(error.error, /elsewhere\.invalid/);
    assert.equal(fs.readFileSync(lock, 'utf8'), bytes);
  });

  await test('[S4] unreadable holders are refused and untouched', () => {
    for (const bytes of ['12345', 'not json', JSON.stringify({ pid: String(deadPid()), host: os.hostname() }),
      JSON.stringify({ pid: -1, host: os.hostname() })]) {
      const { run, lock } = lockRun();
      fs.writeFileSync(lock, bytes);
      const error = stateClaim(run, true);
      assert.equal(error.code, 'ELOCKED', bytes);
      assert.equal(fs.readFileSync(lock, 'utf8'), bytes);
    }
  });

  await test('[S5] a recovery in progress is refused; a dead guard is named, and removing it recovers the lock', () => {
    const { run, lock, guard } = lockRun();
    const lockBytes = JSON.stringify({ pid: deadPid(), host: os.hostname() });
    fs.writeFileSync(lock, lockBytes);
    fs.writeFileSync(guard, JSON.stringify({ pid: process.pid, host: os.hostname() }));
    let error = stateClaim(run, true);
    assert.equal(error.code, 'ELOCKED');
    assert.match(error.error, /another process is recovering/);
    assert.equal(fs.readFileSync(lock, 'utf8'), lockBytes);
    fs.writeFileSync(guard, JSON.stringify({ pid: deadPid(), host: os.hostname() }));
    error = stateClaim(run, true);
    assert.equal(error.code, 'ELOCKED');
    assert.ok(error.error.includes(guard), 'the refusal names the guard file');
    assert.equal(fs.readFileSync(lock, 'utf8'), lockBytes);
    fs.unlinkSync(guard);
    assert.equal(stateClaim(run).claims.length, 1);
  });

  await test('[S6] a lock taken by a live writer during recovery is never removed', () => {
    const { run, lock } = lockRun();
    fs.writeFileSync(lock, JSON.stringify({ pid: deadPid(), host: os.hostname() }));
    const live = JSON.stringify({ pid: process.pid, host: require('node:os').hostname() });
    // Once the recovering writer holds the guard, a live writer replaces the lock.
    const code = `const fs=require('fs'),open=fs.openSync;fs.openSync=(p,...a)=>{const d=open(p,...a);` +
      `if(String(p).endsWith('.dispatcher.lock.recover')){fs.unlinkSync(process.argv[3]);fs.writeFileSync(process.argv[3],process.argv[4]);}return d;};` +
      `try{require(process.argv[1]).claim(process.argv[2],'${OWNER}',1);process.exit(0);}catch(e){process.stderr.write(JSON.stringify({error:e.message,code:e.code}));process.exit(3);}`;
    const child = spawnSync(process.execPath, ['-e', code, statePath, run, lock, live], { encoding: 'utf8', timeout: 15000 });
    assert.equal(child.status, 3, 'claim must be refused: ' + child.stderr);
    assert.equal(parseError(child.stderr).code, 'ELOCKED');
    assert.equal(fs.readFileSync(lock, 'utf8'), live);
  });

  // ---- D3: no cap; exact retry call; deep blocking ----

  await test('[S7] deep blocking is set and undone; retries are uncapped and the returned call works', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    for (let n = 1; n <= 3; n += 1) {
      runStep(run, 'B', 'FAILED');
      const view = dispatch('next', run);
      assert.deepEqual(rows(view, 'blocked'), ['C', 'D']);
      assert.deepEqual(view.progress.failed.map((row) => [row.step, row.attempts]), [['B', n]]);
      const action = view.actions.find((item) => item.action === 'retry');
      assert.equal(action.step, 'B');
      assert.equal(action.attempts, n);
      assert.match(action.reason, /FAILED/);
      assert.deepEqual(action.call.argv.slice(2), ['retry', run]);
      runCall(action.call, 'attempt ' + (n + 1) + ' uses a different fixture');
      const after = dispatch('next', run);
      assert.deepEqual(rows(after, 'blocked'), []);
      assert.ok(after.ready.includes('B'));
    }
    runStep(run, 'B');
    assert.ok(dispatch('next', run).ready.includes('C'));
  });

  // ---- D4: verified BLOCKED routes to replanning ----

  await test('[S8] replan stops new work, lets in-flight work settle, then says the run cannot complete', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    const eAttempt = claimOne(run, 'E');
    const eStarted = launch(run, 'E', eAttempt);
    const b = runStep(run, 'B', 'BLOCKED', { disposition: 'replan' });
    assert.equal(b.result.outcome, 'rejected');
    let view = dispatch('next', run);
    assert.deepEqual(view.ready, []);
    assert.deepEqual(view.replan.steps.map((row) => row.step), ['B']);
    assert.deepEqual(rows(view, 'blocked'), ['C', 'D']);
    const replan = view.actions.find((item) => item.action === 'replan');
    assert.equal(replan.step, 'B');
    assert.equal(view.actions.some((item) => item.action === 'claim'), false);
    assert.equal(view.actions.some((item) => item.action === 'collect' && item.step === 'E'), true);
    assert.doesNotMatch(view.instruction, /cannot complete/);
    const retried = dispatch('retry', run, { owner: OWNER, attempt: b.attempt, confirmed_stopped: true, reason: 'try again' }, true);
    assert.equal(retried.code, 'EREPLAN');
    reportAndSettle(run, 'E', eAttempt, eStarted, 'SUCCEEDED', {});
    const claim = dispatch('claim', run, { owner: OWNER, steps: ['F'] }, true);
    assert.equal(claim.code, 'EREPLAN');
    view = dispatch('next', run);
    assert.deepEqual(view.ready, []);
    assert.deepEqual(view.replan.accepted, ['A', 'E']);
    assert.deepEqual(view.replan.unfinished, ['B', 'C', 'D', 'F']);
    assert.match(view.instruction, /cannot complete/);
    assert.equal(view.complete, false);
  });

  await test('[S9] a claimed attempt is refused a fresh start and released by its returned call', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    const eAttempt = claimOne(run, 'E');
    runStep(run, 'B', 'BLOCKED', { disposition: 'replan' });
    const workspace = path.join(root, 'ws', eAttempt);
    fs.mkdirSync(workspace, { recursive: true });
    const start = dispatch('start', run, {
      owner: OWNER, attempt: eAttempt,
      context: { workspace, write_scope: ['src/E.json'], resources: [], ready_evidence: evidence({ step: 'E' }) },
    }, true);
    assert.equal(start.code, 'EREPLAN');
    const release = dispatch('next', run).actions.find((item) => item.action === 'release');
    assert.equal(release.step, 'E');
    runCall(release.call, 'the run is being replanned');
    const view = dispatch('next', run);
    assert.deepEqual(view.ready, []);
    assert.equal(view.actions.some((item) => item.step === 'E'), false);
    assert.match(view.instruction, /cannot complete/);
  });

  await test('[S10] disposition shapes: only replan with passed false, on any receipt status', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    const attempt = claimOne(run, 'B');
    const started = launch(run, 'B', attempt);
    let refused = reportAndSettle(run, 'B', attempt, started, 'BLOCKED', { disposition: 'replan', passed: true }, true);
    assert.match(refused.result.error, /requires passed: false/);
    const receipt = dispatch('receipt', run, { attempt });
    refused = dispatch('settle', run, { owner: OWNER, attempt, verification: {
      receipt_sha256: receipt.sha256, passed: false, reason: 'x', evidence: evidence({ x: 1 }), disposition: 'REPLAN',
    } }, true);
    assert.match(refused.error, /must be "replan"/);
    // A SUCCEEDED receipt whose criteria cannot be confirmed here also goes to planning.
    const other = newRun(DEEP);
    runStep(other, 'A');
    const succeeded = runStep(other, 'B', 'SUCCEEDED', { passed: false, disposition: 'replan', reason: 'criterion needs execution that is unavailable here' });
    assert.equal(succeeded.result.outcome, 'rejected');
    assert.deepEqual(dispatch('next', other).replan.steps.map((row) => row.step), ['B']);
  });

  await test('[S11] a replan settlement replays idempotently; a changed disposition conflicts', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    const b = runStep(run, 'B', 'BLOCKED', { disposition: 'replan' });
    const replay = dispatch('settle', run, { owner: OWNER, attempt: b.attempt, verification: b.verification });
    assert.equal(replay.outcome, 'rejected');
    const { disposition, ...without } = b.verification;
    assert.equal(disposition, 'replan');
    const conflict = dispatch('settle', run, { owner: OWNER, attempt: b.attempt, verification: without }, true);
    assert.match(conflict.error, /conflicting settlement/);
  });

  await test('[S12] other failed steps are not offered a retry while replanning', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    runStep(run, 'E', 'FAILED');
    assert.equal(dispatch('next', run).actions.some((item) => item.action === 'retry' && item.step === 'E'), true);
    runStep(run, 'B', 'BLOCKED', { disposition: 'replan' });
    const view = dispatch('next', run);
    assert.equal(view.actions.some((item) => item.action === 'retry'), false);
    assert.deepEqual(view.actions.map((item) => item.action), ['replan']);
  });

  // ---- D5: lost state fails closed with the recovery named ----

  await test('[S13] a lost state file or settled receipt fails closed and names a new run', () => {
    const run = newRun(DEEP);
    const a = runStep(run, 'A');
    fs.unlinkSync(path.join(run, 'inbox', a.attempt + '.json'));
    let error = dispatch('next', run, undefined, true);
    assert.equal(error.code, 'ESTATELOST');
    assert.match(error.error, /Start a new run/);
    const other = newRun(DEEP);
    fs.unlinkSync(path.join(other, 'plan-dispatcher-state.json'));
    error = dispatch('next', other, undefined, true);
    assert.equal(error.code, 'ESTATELOST');
    assert.match(error.error, /Start a new run/);
  });

  // ---- U3 (pinned): takeover while replanning ----

  await test('[S14] owner takeover keeps the replan and still refuses claims', () => {
    const run = newRun(DEEP);
    runStep(run, 'A');
    runStep(run, 'B', 'BLOCKED', { disposition: 'replan' });
    dispatch('takeover', run, { oldOwner: OWNER, newOwner: 'parent-2', confirmed_stopped: true, reason: 'handoff' });
    const view = dispatch('next', run);
    assert.deepEqual(view.replan.steps.map((row) => row.step), ['B']);
    const claim = dispatch('claim', run, { owner: 'parent-2', steps: ['E'] }, true);
    assert.equal(claim.code, 'EREPLAN');
  });

  if (failures) {
    console.log(failures + ' failed; fixture root retained: ' + root);
    process.exitCode = 1;
  } else {
    fs.rmSync(root, { recursive: true, force: true });
  }
}

main();
