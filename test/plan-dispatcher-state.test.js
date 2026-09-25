'use strict';

// Deterministic regression coverage for the state primitive. The fake host is
// deliberately only a durable ledger; this file never launches a model.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');

const statePath = path.resolve(__dirname, '../skills/plan-dispatcher/scripts/state.js');
const state = require(statePath);
const fake = require('./fixtures/plan-dispatcher/fake-host.js');
const resolveLookup = require('./fixtures/plan-dispatcher/resolve-lookup.js');
const STATE_FILE = 'plan-dispatcher-state.json';
const RETIRED_STATE_FILE = 'state.json';
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'backchain-dispatcher-state-test-'));
const observations = [];

const hash = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

function save(value, target) {
  const file = target || path.join(root, crypto.randomUUID() + '.json');
  fs.writeFileSync(file, JSON.stringify(value), { flag: 'wx' });
  return file;
}

function evidence(value) {
  const file = save(value);
  return { path: file, sha256: hash(fs.readFileSync(file)) };
}

function graph() {
  return {
    version: 1,
    steps: [
      { id: 'A', deps: [] },
      { id: 'B', deps: ['A'] },
      { id: 'C', deps: ['A'] },
      { id: 'D', deps: ['B', 'C'] },
    ],
  };
}

function cli(operation, dir, input, expectFailure = false) {
  const result = spawnSync(
    process.execPath,
    [statePath, operation, dir, ...(input === undefined ? [] : [save(input)])],
    { encoding: 'utf8', timeout: 15000 }
  );
  assert.ifError(result.error);
  if (expectFailure) {
    assert.notEqual(result.status, 0, `${operation} unexpectedly succeeded`);
    return result;
  }
  assert.equal(result.status, 0, `${operation}: ${result.stderr}`);
  return JSON.parse(result.stdout);
}

function init(inputGraph = graph()) {
  const dir = path.join(root, crypto.randomUUID());
  return { dir, state: cli('init', dir, { graph: inputGraph, owner: 'parent-1' }) };
}

function claim(dir, owner = 'parent-1', limit = 10) {
  return cli('claim', dir, { owner, limit }).claims;
}

function started(dir, task, owner = 'parent-1') {
  const packet = cli('start', dir, { owner, attempt: task.attempt });
  assert.equal(packet.action, 'launch');
  cli('launched', dir, {
    owner,
    attempt: task.attempt,
    handle: 'fixture-confirmed-' + task.attempt,
  });
}

function report(dir, task, value = 42, status = 'SUCCEEDED') {
  const envelope = {
    run_id: task.run_id,
    step: task.step,
    attempt: task.attempt,
    status,
    evidence: evidence({ value }),
  };
  cli('report', dir, envelope);
  return envelope;
}

function independentlyVerify(dir, task, owner = 'parent-1') {
  const receipt = cli('receipt', dir, { attempt: task.attempt });
  const bytes = fs.readFileSync(receipt.envelope.evidence.path);
  assert.equal(hash(bytes), receipt.envelope.evidence.sha256);
  const passed = receipt.envelope.status === 'SUCCEEDED' && JSON.parse(bytes).value === 42;
  const verification = {
    receipt_sha256: receipt.sha256,
    passed,
    reason: passed ? 'Independent value check passed' : 'Independent value check failed',
    evidence: evidence({ actual: JSON.parse(bytes).value, expected: 42, passed }),
  };
  const result = cli('settle', dir, { owner, attempt: task.attempt, verification });
  return { verification, result };
}

function finish(dir, task, owner = 'parent-1') {
  started(dir, task, owner);
  report(dir, task);
  return independentlyVerify(dir, task, owner).result;
}

function readStateBytes(dir) {
  return fs.readFileSync(path.join(dir, STATE_FILE));
}

function writeState(dir, value) {
  fs.writeFileSync(path.join(dir, STATE_FILE), JSON.stringify(value, null, 2) + '\n');
}

function canonicalStatePath(dir) {
  return path.join(dir, STATE_FILE);
}

function retiredStatePath(dir) {
  return path.join(dir, RETIRED_STATE_FILE);
}

function context(label, options = {}) {
  const workspace = options.workspace || path.join(root, 'workspaces', label);
  if (!fs.existsSync(workspace)) {
    fs.mkdirSync(workspace, { recursive: true });
  }
  return {
    workspace,
    write_scope: options.write_scope === undefined ? ['src'] : options.write_scope,
    resources: options.resources === undefined ? [label] : options.resources,
    ready_evidence: evidence({ label, ready: true }),
  };
}

function mainContextExecutor(id = 'serial-main-context') {
  return { kind: 'main-context', id };
}

async function test(name, fn) {
  const began = Date.now();
  const detail = await fn();
  observations.push({ name, passed: true, duration_ms: Date.now() - began, ...(detail || {}) });
  console.log('PASS ' + name);
}

// Terminate an actual dispatcher process at a deterministic IPC barrier.
// The external system in this experiment is the explicitly fake host ledger.
async function crashAt(dir, task, point, baseline = false) {
  const code = `const nav=require(process.argv[1]),host=require(process.argv[2]);const dir=process.argv[3],task=JSON.parse(process.argv[4]),point=process.argv[5];
    if(point==='baseline') {host.launch(dir,task.dispatch_key);}
    else { if(point!=='claimed')nav.start(dir,'parent-1',task.attempt);if(['external','confirmed','reported'].includes(point)){const h=host.launch(dir,task.dispatch_key);if(['confirmed','reported'].includes(point))nav.launched(dir,'parent-1',task.attempt,h.handle);} }
    process.send({barrier:point});process.on('message',()=>{});`;
  await new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      ['-e', code, statePath, path.join(__dirname, 'fixtures/plan-dispatcher/fake-host.js'), dir, JSON.stringify(task), baseline ? 'baseline' : point],
      { stdio: ['ignore', 'ignore', 'pipe', 'ipc'], timeout: 10000 }
    );
    let stderr = '';
    let barrier = false;
    child.stderr.on('data', (data) => { stderr += data; });
    child.on('error', reject);
    child.on('message', (message) => {
      if (message.barrier) {
        barrier = true;
        child.kill('SIGKILL');
      }
    });
    child.on('close', (code, signal) => {
      try {
        assert.equal(barrier, true, stderr);
        assert.equal(signal, 'SIGKILL');
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  });
}

async function main() {
  await test('new dispatcher runs use only the canonical state filename', () => {
    const { dir } = init();
    const canonical = canonicalStatePath(dir);
    const retired = retiredStatePath(dir);
    assert.equal(fs.lstatSync(canonical).isFile(), true);
    assert.equal(fs.existsSync(retired), false);
    const before = fs.readFileSync(canonical);
    claim(dir);
    assert.notDeepEqual(fs.readFileSync(canonical), before);
    assert.equal(fs.existsSync(retired), false);
  });

  await test('retired state.json is refused without mutation', () => {
    const { dir } = init();
    const canonical = canonicalStatePath(dir);
    const retired = retiredStatePath(dir);
    const canonicalBytes = fs.readFileSync(canonical);
    for (const [label, retiredBytes, keepCanonical] of [
      ['alongside canonical', canonicalBytes, true],
      ['corrupt alongside canonical', Buffer.from('{not valid JSON}\n'), true],
      ['retired only', canonicalBytes, false],
    ]) {
      fs.writeFileSync(retired, retiredBytes);
      if (!keepCanonical) fs.unlinkSync(canonical);
      const beforeRetired = fs.readFileSync(retired);
      const refused = cli('inspect', dir, undefined, true);
      assert.match(refused.stderr, /retired state\.json \(Plan Dispatcher 0\.1\.0\); not supported/, label);
      assert.deepEqual(fs.readFileSync(retired), beforeRetired, label);
      if (keepCanonical) {
        assert.deepEqual(fs.readFileSync(canonical), canonicalBytes, label);
      } else {
        assert.equal(fs.existsSync(canonical), false, label);
        fs.writeFileSync(canonical, canonicalBytes);
      }
      fs.unlinkSync(retired);
    }
  });

  await test('nonregular or symlink canonical state fails without a fallback', () => {
    const { dir } = init();
    const canonical = canonicalStatePath(dir);
    const saved = path.join(root, crypto.randomUUID() + '.json');
    fs.renameSync(canonical, saved);
    for (const [label, create] of [
      ['symlink', () => fs.symlinkSync(saved, canonical, 'file')],
      ['directory', () => fs.mkdirSync(canonical)],
    ]) {
      create();
      const beforeSaved = fs.readFileSync(saved);
      const refused = cli('inspect', dir, undefined, true);
      assert.match(refused.stderr, /regular.*state|state.*regular/i, label);
      assert.deepEqual(fs.readFileSync(saved), beforeSaved, label);
      fs.rmSync(canonical, { recursive: true });
    }
  });

  await test('negative control: status-only resume launches the external work twice', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'baseline', true);
    // A naive caller sees claimed with no handle and retries the launch.
    fake.launch(dir, task.dispatch_key);
    assert.equal(fake.lookup(dir, task.dispatch_key).length, 2);
    return { external_launches: 2 };
  });

  await test('negative control: trusting SUCCEEDED unlocks a successor with the wrong result', () => {
    const result = { status: 'SUCCEEDED', artifact: { value: 0 } };
    const naiveAccepted = result.status === 'SUCCEEDED';
    assert.equal(naiveAccepted, true);
    assert.notEqual(result.artifact.value, 42);
    return { false_acceptance: true };
  });

  await test('matched host-capability control: status-only state can also reconcile a known launch', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'baseline', true);
    const matches = fake.lookup(dir, task.dispatch_key);
    assert.equal(matches.length, 1);
    // Same stable dispatch key and lookup capability as the candidate. No retry.
    assert.equal(fake.read(dir).length, 1);
    return { state_design: 'status-only', host_capability: 'fake lookup by same dispatch key', external_launches: 1 };
  });

  await test('claim before intent survives process death and permits exactly one first launch', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'claimed');
    assert.equal(cli('inspect', dir).active[0].recovery, 'start');
    const packet = cli('start', dir, { owner: 'parent-1', attempt: task.attempt });
    assert.equal(packet.action, 'launch');
    assert.equal(packet.dispatch_key, task.dispatch_key);
    const handle = fake.launch(dir, task.dispatch_key);
    cli('launched', dir, { owner: 'parent-1', attempt: task.attempt, handle: handle.handle });
    assert.equal(fake.read(dir).length, 1);
    assert.equal(cli('start', dir, { owner: 'parent-1', attempt: task.attempt }).action, 'reconcile');
  });

  await test('intent before external launch is conservatively uncertain after process death', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'intent');
    assert.equal(cli('inspect', dir).active[0].recovery, 'reconcile');
    assert.equal(fake.read(dir).length, 0);
    assert.equal(cli('start', dir, { owner: 'parent-1', attempt: task.attempt }).action, 'reconcile');
    return { actual_launches: 0, recovery: 'uncertain; no automatic retry', liveness: 'requires reconciliation or confirmed safe retry' };
  });

  await test('launch before handle persistence reconciles through a capable external host', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'external');
    assert.equal(cli('inspect', dir).active[0].recovery, 'reconcile');
    assert.equal(cli('inspect', dir).active[0].dispatch_key, task.dispatch_key);
    const matches = fake.lookup(dir, task.dispatch_key);
    assert.equal(matches.length, 1);
    cli('launched', dir, { owner: 'parent-1', attempt: task.attempt, handle: matches[0].handle });
    assert.equal(cli('inspect', dir).active[0].recovery, 'collect');
    assert.equal(fake.read(dir).length, 1);
    return { host_capability: 'fake durable lookup by dispatch key', external_launches: 1 };
  });

  await test('missing host lookup leaves unconfirmed launch blocked without duplication', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'external');
    const snapshot = cli('inspect', dir);
    assert.equal(snapshot.active[0].recovery, 'reconcile');
    assert.equal(snapshot.complete, false);
    assert.equal(cli('start', dir, { owner: 'parent-1', attempt: task.attempt }).action, 'reconcile');
    assert.equal(fake.read(dir).length, 1);
    return { host_capability: 'unavailable', automatic_progress: false, duplicate_launches: 0 };
  });

  await test('persisted native handle survives dispatcher process death', async () => {
    const { dir } = init();
    const task = claim(dir)[0];
    await crashAt(dir, task, 'confirmed');
    const snapshot = cli('inspect', dir);
    assert.equal(snapshot.active[0].recovery, 'collect');
    assert.equal(snapshot.active[0].handle, fake.read(dir)[0].handle);
  });

  await test('native inventory policy refuses zero and ambiguous task matches', () => {
    const key = '/root/expected-attempt';
    assert.equal(resolveLookup(key, []).action, 'reconcile');
    assert.equal(resolveLookup(key, [{ agent_name: key }, { agent_name: key }]).action, 'reconcile');
    assert.deepEqual(
      resolveLookup(key, [{ agent_name: '/root/unrelated' }, { agent_name: key }]),
      { action: 'record-handle', handle: key, matches: 1 }
    );
  });

  await test('worker report changes only inbox; cold dispatcher verification unlocks successors', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    started(dir, task);
    const before = readStateBytes(dir);
    const envelope = report(dir, task);
    assert.equal(readStateBytes(dir).equals(before), true);
    let snapshot = cli('inspect', dir);
    assert.deepEqual(snapshot.ready, []);
    assert.equal(snapshot.active[0].recovery, 'verify');
    const checked = independentlyVerify(dir, task);
    snapshot = cli('inspect', dir);
    assert.deepEqual(snapshot.ready, ['B', 'C']);
    const revision = snapshot.revision;
    cli('report', dir, envelope);
    cli('settle', dir, { owner: 'parent-1', attempt: task.attempt, verification: checked.verification });
    assert.equal(cli('inspect', dir).revision, revision);
  });

  await test('receipt before saved launch confirmation cannot be accepted prematurely', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    cli('start', dir, { owner: 'parent-1', attempt: task.attempt });
    report(dir, task);
    const receipt = cli('receipt', dir, { attempt: task.attempt });
    const verification = {
      receipt_sha256: receipt.sha256,
      passed: true,
      reason: 'fixture check',
      evidence: evidence({ passed: true }),
    };
    cli('settle', dir, { owner: 'parent-1', attempt: task.attempt, verification }, true);
    assert.deepEqual(cli('inspect', dir).accepted, []);
    cli('launched', dir, { owner: 'parent-1', attempt: task.attempt, handle: 'fixture-reconciled' });
    cli('settle', dir, { owner: 'parent-1', attempt: task.attempt, verification });
    assert.deepEqual(cli('inspect', dir).ready, ['B', 'C']);
  });

  await test('false success and explicit worker failure remain unaccepted', () => {
    for (const [value, status] of [[0, 'SUCCEEDED'], [42, 'FAILED'], [42, 'BLOCKED']]) {
      const { dir } = init();
      const task = claim(dir)[0];
      started(dir, task);
      report(dir, task, value, status);
      independentlyVerify(dir, task);
      const snapshot = cli('inspect', dir);
      assert.deepEqual(snapshot.accepted, []);
      assert.deepEqual(snapshot.ready, []);
      assert.equal(snapshot.complete, false);
    }
  });

  await test('retry requires stoppage and fences late reports from the old attempt', () => {
    const { dir } = init();
    const old = claim(dir)[0];
    started(dir, old);
    const oldEnvelope = {
      run_id: old.run_id,
      step: old.step,
      attempt: old.attempt,
      status: 'SUCCEEDED',
      evidence: evidence({ value: 42 }),
    };
    cli('retry', dir, { owner: 'parent-1', attempt: old.attempt, confirmed_stopped: false, reason: 'unknown' }, true);
    cli('retry', dir, { owner: 'parent-1', attempt: old.attempt, confirmed_stopped: true, reason: 'test process exited' });
    const fresh = claim(dir)[0];
    assert.notEqual(fresh.attempt, old.attempt);
    cli('report', dir, oldEnvelope, true);
    finish(dir, fresh);
    assert.deepEqual(cli('inspect', dir).ready, ['B', 'C']);
  });

  await test('rejected branch can be retried and only its accepted replacement unlocks join', () => {
    const { dir } = init();
    finish(dir, claim(dir)[0]);
    const tasks = claim(dir);
    const b = tasks.find((task) => task.step === 'B');
    const old = tasks.find((task) => task.step === 'C');
    finish(dir, b);
    started(dir, old);
    report(dir, old, 0);
    independentlyVerify(dir, old);
    assert.deepEqual(cli('inspect', dir).ready, []);
    cli('retry', dir, { owner: 'parent-1', attempt: old.attempt, confirmed_stopped: true, reason: 'fixture result producer exited' });
    assert.deepEqual(cli('inspect', dir).ready, ['C']);
    const fresh = claim(dir)[0];
    assert.notEqual(old.attempt, fresh.attempt);
    finish(dir, fresh);
    assert.deepEqual(cli('inspect', dir).ready, ['D']);
  });

  await test('owner takeover preserves in-flight work and rejects the previous dispatcher', () => {
    const { dir, state: initial } = init();
    const task = claim(dir)[0];
    started(dir, task);
    report(dir, task);
    cli('takeover', dir, { oldOwner: 'parent-1', newOwner: 'parent-2', confirmed_stopped: false, reason: 'unknown' }, true);
    cli('takeover', dir, { oldOwner: 'parent-1', newOwner: 'parent-2', confirmed_stopped: true, reason: 'test dispatcher process confirmed exited' });
    const snapshot = cli('inspect', dir);
    assert.equal(snapshot.owner, 'parent-2');
    assert.equal(snapshot.generation, initial.generation + 1);
    assert.equal(snapshot.active[0].attempt, task.attempt);
    cli('takeover', dir, { oldOwner: 'parent-2', newOwner: 'parent-1', confirmed_stopped: true, reason: 'would reactivate stale identity' }, true);
    cli('launched', dir, { owner: 'parent-1', attempt: task.attempt, handle: 'stale-owner-handle' }, true);
    cli('retry', dir, { owner: 'parent-1', attempt: task.attempt, confirmed_stopped: true, reason: 'stale owner' }, true);
    const receipt = cli('receipt', dir, { attempt: task.attempt });
    cli('settle', dir, {
      owner: 'parent-1',
      attempt: task.attempt,
      verification: { receipt_sha256: receipt.sha256, passed: true, reason: 'stale owner', evidence: evidence({ passed: true }) },
    }, true);
    cli('claim', dir, { owner: 'parent-1', limit: 1 }, true);
    independentlyVerify(dir, task, 'parent-2');
    assert.deepEqual(cli('inspect', dir).ready, ['B', 'C']);
  });

  await test('out-of-order independent results join only after both acceptances', () => {
    const { dir } = init();
    finish(dir, claim(dir)[0]);
    const tasks = claim(dir);
    assert.deepEqual(tasks.map((task) => task.step), ['B', 'C']);
    finish(dir, tasks.find((task) => task.step === 'C'));
    assert.deepEqual(cli('inspect', dir).ready, []);
    finish(dir, tasks.find((task) => task.step === 'B'));
    assert.deepEqual(cli('inspect', dir).ready, ['D']);
    finish(dir, claim(dir)[0]);
    assert.equal(cli('inspect', dir).complete, true);
  });

  await test('disconnected required work prevents completion through rejection and retry', () => {
    const inputGraph = graph();
    inputGraph.steps.push({ id: 'AUDIT', deps: [] });
    const { dir } = init(inputGraph);
    const first = state.claim(dir, 'parent-1', 2, ['A', 'AUDIT']).claims;
    const audit = first.find(task => task.step === 'AUDIT');
    finish(dir, first.find(task => task.step === 'A'));
    for (const task of claim(dir)) finish(dir, task);
    finish(dir, claim(dir)[0]);
    let snapshot = cli('inspect', dir);
    assert.deepEqual(snapshot.accepted, ['A', 'B', 'C', 'D']);
    assert.equal(snapshot.complete, false, 'the main component cannot complete the run alone');
    started(dir, audit);
    report(dir, audit, 42, 'FAILED');
    independentlyVerify(dir, audit);
    assert.equal(cli('inspect', dir).complete, false, 'failed disconnected work remains required');
    state.retry(dir, 'parent-1', audit.attempt, { confirmed_stopped: true, reason: 'fixture worker stopped' });
    const replacement = claim(dir)[0];
    assert.equal(replacement.step, 'AUDIT');
    started(dir, replacement);
    report(dir, replacement);
    assert.equal(cli('inspect', dir).complete, false, 'a successful report still needs acceptance');
    independentlyVerify(dir, replacement);
    snapshot = cli('inspect', dir);
    assert.deepEqual(snapshot.accepted, ['A', 'B', 'C', 'D', 'AUDIT']);
    assert.equal(snapshot.complete, true);
  });

  await test('capacity limits and eager successors do not impose a wave barrier', () => {
    const inputGraph = {
      version: 1,
      steps: [
        { id: 'A', deps: [] },
        { id: 'Z', deps: [] },
        { id: 'B', deps: ['A'] },
        { id: 'D', deps: ['B', 'Z'] },
      ],
    };
    const { dir } = init(inputGraph);
    const a = claim(dir, 'parent-1', 1);
    assert.equal(a.length, 1);
    assert.equal(a[0].step, 'A');
    const z = claim(dir, 'parent-1', 1)[0];
    assert.equal(z.step, 'Z');
    finish(dir, a[0]);
    assert.deepEqual(cli('inspect', dir).ready, ['B']);
  });

  await test('cross-run and conflicting reports and evidence drift reject without state mutation', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    started(dir, task);
    const envelope = report(dir, task);
    cli('report', dir, { ...envelope, run_id: 'other-run' }, true);
    cli('report', dir, { ...envelope, evidence: evidence({ value: 1 }) }, true);
    fs.appendFileSync(envelope.evidence.path, 'drift');
    const receiptPath = path.join(dir, 'inbox', task.attempt + '.json');
    const bytes = fs.readFileSync(receiptPath);
    const before = readStateBytes(dir);
    cli('settle', dir, {
      owner: 'parent-1',
      attempt: task.attempt,
      verification: {
        receipt_sha256: hash(bytes),
        passed: true,
        reason: 'cannot trust changed artifact',
        evidence: evidence({ passed: true }),
      },
    }, true);
    assert.equal(readStateBytes(dir).equals(before), true);
  });

  await test('snapshot crash around rename preserves old/new state and does not steal orphan lock', () => {
    for (const when of ['before', 'after']) {
      const { dir } = init();
      const task = claim(dir)[0];
      const code = `const fs=require('fs'),old=fs.renameSync;fs.renameSync=(...a)=>{if(a[1].endsWith('plan-dispatcher-state.json')){if(process.argv[4]==='before')process.exit(77);old(...a);process.exit(77);}return old(...a);};require(process.argv[1]).start(process.argv[2],'parent-1',process.argv[3]);`;
      const result = spawnSync(process.execPath, ['-e', code, statePath, dir, task.attempt, when], { encoding: 'utf8', timeout: 10000 });
      assert.equal(result.status, 77, result.stderr);
      const snapshot = cli('inspect', dir);
      assert.equal(snapshot.active[0].status, when === 'before' ? 'claimed' : 'launching');
      assert.ok(fs.existsSync(path.join(dir, '.dispatcher.lock')));
      if (when === 'after') {
        cli('claim', dir, { owner: 'parent-1', limit: 1 }, true);
      }
      // Exact test-owned process has exited. This is fixture cleanup only.
      fs.unlinkSync(path.join(dir, '.dispatcher.lock'));
      assert.equal(
        cli('start', dir, { owner: 'parent-1', attempt: task.attempt }).action,
        when === 'before' ? 'launch' : 'reconcile'
      );
    }
  });

  await test('inbox publication crash preserves canonical state and exposes only a full receipt', () => {
    for (const when of ['before', 'after']) {
      const { dir } = init();
      const task = claim(dir)[0];
      started(dir, task);
      const before = readStateBytes(dir);
      const envelope = {
        run_id: task.run_id,
        step: task.step,
        attempt: task.attempt,
        status: 'SUCCEEDED',
        evidence: evidence({ value: 42 }),
      };
      const code = `const fs=require('fs'),old=fs.linkSync;fs.linkSync=(...a)=>{if(a[1].includes('/inbox/')){if(process.argv[3]==='before')process.exit(77);old(...a);process.exit(77);}return old(...a);};require(process.argv[1]).report(process.argv[2],JSON.parse(process.argv[4]));`;
      const result = spawnSync(process.execPath, ['-e', code, statePath, dir, when, JSON.stringify(envelope)], { encoding: 'utf8', timeout: 10000 });
      assert.equal(result.status, 77, result.stderr);
      assert.equal(readStateBytes(dir).equals(before), true);
      const target = path.join(dir, 'inbox', task.attempt + '.json');
      assert.equal(fs.existsSync(target), when === 'after');
      if (when === 'after') {
        assert.deepEqual(JSON.parse(fs.readFileSync(target)), envelope);
      }
      fs.unlinkSync(path.join(dir, '.dispatcher.lock'));
      cli('report', dir, envelope);
      independentlyVerify(dir, task);
      assert.deepEqual(cli('inspect', dir).ready, ['B', 'C']);
    }
  });

  await test('acceptance crash before/after rename preserves join gating and idempotent replay', () => {
    for (const when of ['before', 'after']) {
      const { dir } = init();
      const task = claim(dir)[0];
      started(dir, task);
      report(dir, task);
      const receipt = cli('receipt', dir, { attempt: task.attempt });
      assert.equal(JSON.parse(fs.readFileSync(receipt.envelope.evidence.path)).value, 42);
      const verification = {
        receipt_sha256: receipt.sha256,
        passed: true,
        reason: 'independent value42 check',
        evidence: evidence({ actual: 42, expected: 42, passed: true }),
      };
      const revision = cli('inspect', dir).revision;
      const code = `const fs=require('fs'),old=fs.renameSync;fs.renameSync=(...a)=>{if(a[1].endsWith('plan-dispatcher-state.json')){if(process.argv[4]==='before')process.exit(77);old(...a);process.exit(77);}return old(...a);};require(process.argv[1]).settle(process.argv[2],'parent-1',process.argv[3],JSON.parse(process.argv[5]));`;
      const result = spawnSync(process.execPath, ['-e', code, statePath, dir, task.attempt, when, JSON.stringify(verification)], { encoding: 'utf8', timeout: 10000 });
      assert.equal(result.status, 77, result.stderr);
      const interrupted = cli('inspect', dir);
      assert.deepEqual(interrupted.accepted, when === 'after' ? ['A'] : []);
      assert.deepEqual(interrupted.ready, when === 'after' ? ['B', 'C'] : []);
      fs.unlinkSync(path.join(dir, '.dispatcher.lock'));
      cli('settle', dir, { owner: 'parent-1', attempt: task.attempt, verification });
      const recovered = cli('inspect', dir);
      assert.deepEqual(recovered.ready, ['B', 'C']);
      assert.equal(recovered.revision, revision + 1);
    }
  });

  await test('busy report lock leaves no partial receipt and exact retry succeeds', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    started(dir, task);
    const envelope = {
      run_id: task.run_id,
      step: task.step,
      attempt: task.attempt,
      status: 'SUCCEEDED',
      evidence: evidence({ value: 42 }),
    };
    const before = readStateBytes(dir);
    const lock = path.join(dir, '.dispatcher.lock');
    fs.writeFileSync(lock, 'test-owned live critical section', { flag: 'wx' });
    const result = cli('report', dir, envelope, true);
    assert.match(result.stderr, /lock.*held/);
    assert.equal(fs.existsSync(path.join(dir, 'inbox', task.attempt + '.json')), false);
    assert.equal(readStateBytes(dir).equals(before), true);
    fs.unlinkSync(lock);
    cli('report', dir, envelope);
    independentlyVerify(dir, task);
    assert.deepEqual(cli('inspect', dir).ready, ['B', 'C']);
  });

  await test('12 pairs of concurrent inbox reporters retain both results with bounded busy retry', async () => {
    let busy = 0;
    for (let round = 0; round < 12; round += 1) {
      const { dir } = init();
      finish(dir, claim(dir)[0]);
      const tasks = claim(dir);
      tasks.forEach((task) => started(dir, task));
      const envelopes = tasks.map((task) => ({
        run_id: task.run_id,
        step: task.step,
        attempt: task.attempt,
        status: 'SUCCEEDED',
        evidence: evidence({ value: 42 }),
      }));
      const before = readStateBytes(dir);
      const results = await Promise.all(envelopes.map((envelope) => new Promise((resolve, reject) => {
        const child = spawn(process.execPath, [statePath, 'report', dir, save(envelope)], { timeout: 10000 });
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (data) => { stdout += data; });
        child.stderr.on('data', (data) => { stderr += data; });
        child.on('error', reject);
        child.on('close', (code) => resolve({ code, stdout, stderr }));
      })));
      for (let index = 0; index < results.length; index += 1) {
        if (results[index].code !== 0) {
          assert.match(results[index].stderr, /lock.*held/);
          busy += 1;
          cli('report', dir, envelopes[index]);
        }
      }
      assert.equal(readStateBytes(dir).equals(before), true);
      tasks.forEach((task) => independentlyVerify(dir, task));
      assert.deepEqual(cli('inspect', dir).ready, ['D']);
    }
    return { pairs: 12, reporters: 24, observed_busy_retries: busy };
  });

  await test('hydration rejects frozen graph, state-attempt, and accepted-evidence drift', () => {
    {
      const { dir } = init();
      const raw = JSON.parse(readStateBytes(dir));
      raw.graph_sha256 = '0'.repeat(64);
      writeState(dir, raw);
      assert.match(cli('inspect', dir, undefined, true).stderr, /graph.*SHA|SHA.*graph|identity/i);
    }
    {
      const { dir } = init();
      const task = claim(dir)[0];
      const raw = JSON.parse(readStateBytes(dir));
      raw.attempts[task.attempt].step = 'not-the-claimed-step';
      writeState(dir, raw);
      assert.match(cli('inspect', dir, undefined, true).stderr, /attempt|state/i);
    }
    for (const changedArtifact of ['reported', 'verification']) {
      const { dir } = init();
      const task = claim(dir)[0];
      started(dir, task);
      const envelope = report(dir, task);
      const checked = independentlyVerify(dir, task);
      fs.appendFileSync(
        changedArtifact === 'reported' ? envelope.evidence.path : checked.verification.evidence.path,
        'drift'
      );
      assert.match(cli('inspect', dir, undefined, true).stderr, /evidence|SHA|artifact/i);
    }
  });

  await test('exact selected claims reject invalid bundles atomically', () => {
    const inputGraph = {
      version: 1,
      steps: [
        { id: 'A', deps: [] },
        { id: 'Z', deps: [] },
        { id: 'B', deps: ['A'] },
      ],
    };
    const { dir } = init(inputGraph);
    const before = readStateBytes(dir);
    for (const selection of [['missing'], ['A', 'A'], ['B']]) {
      assert.throws(() => state.claim(dir, 'parent-1', 2, selection), /selection|ready|unknown|duplicate/i);
      assert.equal(readStateBytes(dir).equals(before), true, `${selection.join(',')} changes no claim state`);
    }
    const selected = state.claim(dir, 'parent-1', 2, ['Z', 'A']);
    assert.deepEqual(selected.claims.map((task) => task.step).sort(), ['A', 'Z']);
    assert.deepEqual(state.inspect(dir).ready, []);
  });

  await test('start validates bounded write scopes and rejects run workspace aliases', () => {
    const invalidScopes = [['/absolute'], ['../escape'], ['src/../escape'], ['.'], [''], []];
    for (const write_scope of invalidScopes) {
      const { dir } = init();
      const task = claim(dir)[0];
      const before = readStateBytes(dir);
      assert.throws(
        () => state.start(dir, 'parent-1', task.attempt, context('invalid-scope-' + crypto.randomUUID(), { write_scope })),
        /write_scope|scope|relative/i
      );
      assert.equal(readStateBytes(dir).equals(before), true);
    }
    for (const workspace of [
      (dir) => dir,
      (dir) => root,
      (dir) => path.join(dir, 'nested-workspace'),
    ]) {
      const { dir } = init();
      const task = claim(dir)[0];
      const target = workspace(dir);
      if (!fs.existsSync(target)) {
        fs.mkdirSync(target, { recursive: true });
      }
      const before = readStateBytes(dir);
      assert.throws(
        () => state.start(dir, 'parent-1', task.attempt, context('run-overlap-' + crypto.randomUUID(), { workspace: target })),
        /workspace|run|overlap/i
      );
      assert.equal(readStateBytes(dir).equals(before), true);
    }
  });

  await test('context survives cold recovery and conflicting context changes are atomic', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    const original = context('recovery-workspace', { resources: ['recovery-resource'] });
    const frozen = { ...original, workspace: fs.realpathSync(original.workspace) };
    assert.equal(state.start(dir, 'parent-1', task.attempt, original).action, 'launch');
    const snapshot = cli('inspect', dir);
    assert.deepEqual(snapshot.active[0].context, frozen);
    assert.equal(snapshot.graph_sha256.length, 64);
    const described = state.describe(dir);
    assert.equal(described.graph_sha256, snapshot.graph_sha256);
    assert.deepEqual(described.attempts[task.attempt].context, frozen);
    assert.equal(cli('start', dir, { owner: 'parent-1', attempt: task.attempt, context: original }).action, 'reconcile');
    const before = readStateBytes(dir);
    const conflicting = { ...original, resources: ['different-resource'] };
    assert.throws(() => state.start(dir, 'parent-1', task.attempt, conflicting), /context|conflict/i);
    assert.equal(readStateBytes(dir).equals(before), true);
  });

  await test('workspace aliases and external resources block concurrent starts atomically', () => {
    const inputGraph = { version: 1, steps: [{ id: 'B', deps: [] }, { id: 'C', deps: [] }] };
    {
      const { dir } = init(inputGraph);
      const [b, c] = claim(dir);
      const workspace = path.join(root, 'canonical-workspace-' + crypto.randomUUID());
      const alias = path.join(root, 'workspace-alias-' + crypto.randomUUID());
      fs.mkdirSync(workspace, { recursive: true });
      fs.symlinkSync(workspace, alias);
      state.start(dir, 'parent-1', b.attempt, context('canonical', { workspace, resources: ['one'] }));
      const before = readStateBytes(dir);
      assert.throws(
        () => state.start(dir, 'parent-1', c.attempt, context('alias', { workspace: alias, resources: ['two'] })),
        /workspace|overlap|conflict/i
      );
      assert.equal(readStateBytes(dir).equals(before), true);
    }
    {
      const { dir } = init(inputGraph);
      const [b, c] = claim(dir);
      state.start(dir, 'parent-1', b.attempt, context('resource-left', { resources: ['external:shared'] }));
      const before = readStateBytes(dir);
      assert.throws(
        () => state.start(dir, 'parent-1', c.attempt, context('resource-right', { resources: ['external:shared'] })),
        /resource|conflict/i
      );
      assert.equal(readStateBytes(dir).equals(before), true);
    }
  });

  await test('rejected reservations persist until retry and replacement gets a fresh context', () => {
    const inputGraph = { version: 1, steps: [{ id: 'B', deps: [] }, { id: 'C', deps: [] }] };
    const { dir } = init(inputGraph);
    const [b, c] = claim(dir);
    const rejectedContext = context('rejected-left', { resources: ['external:retained'] });
    state.start(dir, 'parent-1', b.attempt, rejectedContext);
    state.launched(dir, 'parent-1', b.attempt, 'fixture-rejected-context');
    report(dir, b, 0);
    independentlyVerify(dir, b);
    const before = readStateBytes(dir);
    assert.throws(
      () => state.start(dir, 'parent-1', c.attempt, context('blocked-right', { resources: ['external:retained'] })),
      /resource|conflict/i
    );
    assert.equal(readStateBytes(dir).equals(before), true);
    state.retry(dir, 'parent-1', b.attempt, { confirmed_stopped: true, reason: 'fixture worker stopped' });
    assert.equal(
      state.start(dir, 'parent-1', c.attempt, context('released-right', { resources: ['external:retained'] })).action,
      'launch'
    );
    const replacement = state.claim(dir, 'parent-1', 1, ['B']).claims[0];
    const freshContext = context('replacement-left', { resources: ['external:fresh'] });
    assert.equal(state.start(dir, 'parent-1', replacement.attempt, freshContext).action, 'launch');
    assert.notDeepEqual(freshContext, rejectedContext);
  });

  await test('main-context start atomically records serial execution, accepts evidence, and unlocks dependencies', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    const assigned = context('serial-accepted');
    const executor = mainContextExecutor('serial-accepted-context');
    const started = state.start(dir, 'parent-1', task.attempt, assigned, executor);
    assert.equal(started.action, 'execute');
    assert.equal(started.status, 'running');
    assert.equal(started.handle, null);
    assert.deepEqual(started.executor, executor);

    const coldRunning = cli('inspect', dir);
    assert.deepEqual(coldRunning.active.map(({ status, recovery, handle, executor: activeExecutor }) =>
      ({ status, recovery, handle, executor: activeExecutor })), [{
      status: 'running', recovery: 'resume', handle: null, executor,
    }]);
    assert.deepEqual(state.describe(dir).attempts[task.attempt].executor, executor);

    report(dir, task);
    assert.equal(cli('inspect', dir).active[0].recovery, 'verify');
    const accepted = independentlyVerify(dir, task).result;
    assert.equal(accepted.outcome, 'accepted');
    assert.deepEqual(accepted.ready, ['B', 'C']);
    assert.equal(state.describe(dir).attempts[task.attempt].handle, null);
    assert.deepEqual(state.describe(dir).attempts[task.attempt].executor, executor);
  });

  await test('main-context replay is inert and mixed execution identities fail atomically', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    const assigned = context('serial-replay');
    const executor = mainContextExecutor('serial-replay-context');
    state.start(dir, 'parent-1', task.attempt, assigned, executor);
    const beforeReplay = readStateBytes(dir);
    assert.equal(state.start(dir, 'parent-1', task.attempt, assigned, executor).action, 'reconcile');
    assert.equal(readStateBytes(dir).equals(beforeReplay), true);

    for (const attempt of [
      () => state.start(dir, 'parent-1', task.attempt, assigned, mainContextExecutor('other-context')),
      () => state.launched(dir, 'parent-1', task.attempt, 'synthetic-native-handle'),
    ]) {
      assert.throws(attempt, /execution identity|main-context executor/i);
      assert.equal(readStateBytes(dir).equals(beforeReplay), true);
    }

    const { dir: nativeDir } = init();
    const nativeTask = claim(nativeDir)[0];
    const nativeContext = context('native-then-serial');
    state.start(nativeDir, 'parent-1', nativeTask.attempt, nativeContext);
    state.launched(nativeDir, 'parent-1', nativeTask.attempt, 'confirmed-native-handle');
    const beforeMixed = readStateBytes(nativeDir);
    assert.throws(
      () => state.start(nativeDir, 'parent-1', nativeTask.attempt, nativeContext, mainContextExecutor('late-serial')),
      /execution identity/i
    );
    assert.equal(readStateBytes(nativeDir).equals(beforeMixed), true);
  });

  await test('main-context executor survives takeover as a caller-attested recovery identity', () => {
    const { dir } = init();
    const task = claim(dir)[0];
    const assigned = context('serial-takeover');
    const executor = mainContextExecutor('serial-takeover-context');
    state.start(dir, 'parent-1', task.attempt, assigned, executor);
    state.takeover(dir, 'parent-1', 'parent-2', {
      confirmed_stopped: true,
      reason: 'original dispatcher has stopped before handoff',
    });
    const cold = cli('inspect', dir);
    assert.equal(cold.owner, 'parent-2');
    assert.deepEqual(cold.active.map(({ recovery, executor: activeExecutor }) =>
      ({ recovery, executor: activeExecutor })), [{ recovery: 'resume', executor }]);
    const beforeReplay = readStateBytes(dir);
    assert.equal(state.start(dir, 'parent-2', task.attempt, assigned, executor).action, 'reconcile');
    assert.equal(readStateBytes(dir).equals(beforeReplay), true);
    assert.throws(
      () => state.start(dir, 'parent-1', task.attempt, assigned, executor),
      /owner does not hold/i
    );
  });

  await test('executor hydration fences malformed and mixed state while retried serial identity remains durable', () => {
    const makeSerial = () => {
      const setup = init();
      const task = claim(setup.dir)[0];
      state.start(setup.dir, 'parent-1', task.attempt, context('serial-hydration-' + crypto.randomUUID()), mainContextExecutor('serial-hydration'));
      return { ...setup, task };
    };
    {
      const { dir, task } = makeSerial();
      const raw = JSON.parse(readStateBytes(dir));
      raw.attempts[task.attempt].executor.id = '';
      writeState(dir, raw);
      assert.match(cli('inspect', dir, undefined, true).stderr, /executor.*id|nonempty/i);
    }
    {
      const { dir, task } = makeSerial();
      const raw = JSON.parse(readStateBytes(dir));
      raw.attempts[task.attempt].handle = 'fabricated-native-handle';
      writeState(dir, raw);
      assert.match(cli('inspect', dir, undefined, true).stderr, /both.*native handle.*executor/i);
    }
    {
      const { dir, task } = makeSerial();
      report(dir, task, 0);
      independentlyVerify(dir, task);
      state.retry(dir, 'parent-1', task.attempt, {
        confirmed_stopped: true,
        reason: 'all serial task-owned commands finished',
      });
      const recovered = state.describe(dir).attempts[task.attempt];
      assert.equal(recovered.status, 'retried');
      assert.equal(recovered.handle, null);
      assert.deepEqual(recovered.executor, mainContextExecutor('serial-hydration'));
      assert.equal(cli('inspect', dir).complete, false);
      const raw = JSON.parse(readStateBytes(dir));
      raw.attempts[task.attempt].executor.kind = 'native';
      writeState(dir, raw);
      assert.match(cli('inspect', dir, undefined, true).stderr, /executor.*main-context/i);
    }
  });

  console.log(JSON.stringify({
    passed: observations.length,
    failed: 0,
    scope: 'real process exits and cold state recovery; external host is a deterministic fixture, not native agent durability',
    observations,
  }));
}

async function run() {
  let passed = false;
  try {
    await main();
    passed = true;
  } finally {
    if (passed) {
      fs.rmSync(root, { recursive: true, force: true });
    } else {
      console.error('Retained fixture root: ' + root);
    }
  }
}

run().catch((error) => {
  console.error(error.stack);
  process.exitCode = 1;
});
