'use strict';

/*
 * T1 scenario harness for Plan Dispatcher (plan phase 1, next step N2).
 *
 * - The fake host holds launched native tasks and completes them in the
 *   scenario's schedule order; it is the durable outside world.
 * - The scripted worker plays each step's outcome, chosen by attempt number
 *   (the packet's prior_attempts), and writes a checkable result value.
 * - The driver is memoryless: it only runs the exact call on an action it was
 *   just given. With `amnesia`, it discards every response after acting and
 *   starts again from the fixed entry `dispatch.js next RUN`, and it also loses
 *   context (seeded, about one time in three) between a start grant and the
 *   launch or work that grant authorizes, which forces reconcile, resume and
 *   never-launched retry recovery.
 * - The oracle is an independent model of the graph. It watches claims,
 *   packets, settlements and progress and asserts invariants I1-I5, I7 and I8
 *   (in-flight work never exceeds the run's capacity).
 *
 * Nothing here launches a model. Scenario format: scenarios/README.md.
 */

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const cli = require('./dispatcher-cli');

const OWNER = 'driver';
const MAX_CALLS = 3000;
const STALL_LIMIT = 25;

// Outcomes advance per reported attempt; a never-launched attempt is not one.
function reportedAttempts(packet) {
  return (packet.prior_attempts || []).filter((item) => item.status !== 'NOT_REPORTED').length;
}

function expectedValue(step) {
  return 'value-of-' + step;
}

class Oracle {
  constructor(graph, capacity) {
    this.graph = graph;
    this.capacity = capacity;
    this.deps = new Map(graph.steps.map((step) => [step.id, step.deps]));
    this.status = new Map(graph.steps.map((step) => [step.id, 'pending']));
    this.acceptedReceipt = new Map();
    this.attempts = new Map(graph.steps.map((step) => [step.id, 0]));
  }

  // I1: a claim names only steps whose dependencies the oracle saw accepted.
  onClaim(steps) {
    for (const step of steps) {
      assert.equal(this.status.get(step), 'pending', 'I1: claimed ' + step + ' while ' + this.status.get(step));
      for (const dep of this.deps.get(step)) {
        assert.equal(this.status.get(dep), 'accepted', 'I1: claimed ' + step + ' before ' + dep + ' was accepted');
      }
      this.status.set(step, 'active');
      this.attempts.set(step, this.attempts.get(step) + 1);
    }
    // I8: in-flight work never exceeds the run's capacity.
    if (this.capacity) {
      const active = [...this.status.values()].filter((value) => value === 'active').length;
      assert.ok(active <= this.capacity, 'I8: ' + active + ' in flight exceeds capacity ' + this.capacity);
    }
  }

  // I2: a packet carries accepted evidence from exactly its step's suppliers.
  onPacket(packet) {
    const deps = this.deps.get(packet.step);
    assert.deepEqual(packet.dependencies.map((item) => item.step).sort(), [...deps].sort(),
      'I2: packet for ' + packet.step + ' names the wrong suppliers');
    for (const item of packet.dependencies) {
      assert.equal(item.receipt_sha256, this.acceptedReceipt.get(item.step),
        'I2: packet for ' + packet.step + ' carries a receipt ' + item.step + ' did not have accepted');
    }
  }

  // The settlement outcome must equal the independent verdict.
  onSettle(step, receiptSha256, verdict, outcome) {
    assert.equal(outcome, verdict ? 'accepted' : 'rejected', 'settlement of ' + step + ' disagrees with verification');
    this.status.set(step, outcome);
    if (verdict) this.acceptedReceipt.set(step, receiptSha256);
  }

  onRetry(step) {
    this.status.set(step, 'pending');
  }

  // I3: blocked steps are exactly those below a rejected step.
  expectedBlocked() {
    const blocked = new Set();
    let changed = true;
    while (changed) {
      changed = false;
      for (const [step, deps] of this.deps) {
        if (blocked.has(step) || this.status.get(step) !== 'pending') continue;
        if (deps.some((dep) => this.status.get(dep) === 'rejected' || blocked.has(dep))) {
          blocked.add(step);
          changed = true;
        }
      }
    }
    return [...blocked].sort();
  }

  onProgress(progress) {
    const reported = progress.blocked.map((row) => row.step).sort();
    assert.deepEqual(reported, this.expectedBlocked(), 'I3: blocked steps differ from the oracle');
  }

  accepted() {
    return this.graph.steps.map((step) => step.id).filter((id) => this.status.get(id) === 'accepted');
  }
}

class Host {
  constructor(schedule) {
    this.tasks = new Map();
    this.order = [];
    this.schedule = schedule;
    this.random = seeded(typeof schedule === 'object' ? schedule.seed : 0);
  }

  launch(packet) {
    const handle = 'HOST-' + packet.attempt;
    this.tasks.set(packet.attempt, { packet, handle, done: false });
    this.order.push(packet.attempt);
    return handle;
  }

  lookup(attempt) {
    return this.tasks.get(attempt) || null;
  }

  // The next running task to finish, by the scenario's schedule.
  nextToFinish() {
    const open = this.order.filter((attempt) => !this.tasks.get(attempt).done);
    if (open.length === 0) return null;
    if (this.schedule === 'lifo') return this.tasks.get(open[open.length - 1]);
    if (typeof this.schedule === 'object') return this.tasks.get(open[Math.floor(this.random() * open.length)]);
    return this.tasks.get(open[0]);
  }
}

function seeded(seed) {
  let value = (seed >>> 0) || 1;
  return () => {
    value = (value * 1664525 + 1013904223) >>> 0;
    return value / 4294967296;
  };
}

class World {
  constructor(root, scenario) {
    this.root = root;
    this.scenario = scenario;
    this.host = new Host(scenario.schedule || 'fifo');
    this.oracle = new Oracle(scenario.graph, scenario.capacity);
    this.faults = scenario.faults || {};
    this.log = [];
    this.lossRandom = seeded(String(scenario.id).split('').reduce((sum, ch) => sum * 31 + ch.charCodeAt(0), 7));
  }

  loseContext() {
    const lost = this.lossRandom() < 0.35;
    if (lost) this.log.push(['lost-context']);
    return lost;
  }

  outcome(step, attemptIndex) {
    const plan = (this.scenario.outcomes || {})[step] || [];
    return plan[Math.min(attemptIndex, plan.length - 1)] || 'SUCCEEDED';
  }

  contextValues(step, attempt) {
    const workspace = path.join(this.root, 'ws', attempt);
    fs.mkdirSync(workspace, { recursive: true });
    const values = {
      workspace,
      write_scope: ['src/' + step + '.json'],
      ready_evidence: cli.evidence(this.root, { step, attempt }),
    };
    if (this.scenario.executor === 'main-context') {
      values.executor = { kind: 'main-context', id: 'scenario-main' };
    }
    return values;
  }

  // The scripted worker: do the step's work and write its result artifact.
  work(packet) {
    this.oracle.onPacket(packet);
    const outcome = this.outcome(packet.step, reportedAttempts(packet));
    const status = outcome === 'FALSE_SUCCESS' ? 'SUCCEEDED' : outcome.split(':')[0];
    const value = outcome === 'SUCCEEDED' ? expectedValue(packet.step) : 'wrong-' + packet.step;
    fs.writeFileSync(packet.outputs.artifact, JSON.stringify({ step: packet.step, attempt: packet.attempt, value }));
    const sha256 = cli.digest(fs.readFileSync(packet.outputs.artifact));
    this.log.push(['work', packet.step, outcome]);
    return { status, sha256 };
  }

  // A native worker reports through its packet's report_argv.
  workNative(task) {
    const packet = task.packet;
    const { status, sha256 } = this.work(packet);
    const envelope = { ...packet.report_envelope, status, evidence: { path: packet.outputs.artifact, sha256 } };
    fs.writeFileSync(packet.outputs.envelope, JSON.stringify(envelope));
    cli.argvRun(packet.report_argv);
    task.done = true;
    if ((this.faults.duplicate_report || []).includes(packet.step)) {
      this.refusedWithoutChange(() => {
        fs.writeFileSync(packet.outputs.envelope, JSON.stringify({ ...envelope, status: 'FAILED' }));
        return cli.argvRun(packet.report_argv, true);
      }, packet.run_directory);
    }
  }

  // I4: a refused callback leaves the dispatcher state byte-identical.
  refusedWithoutChange(action, run) {
    const file = path.join(run, 'plan-dispatcher-state.json');
    const before = fs.readFileSync(file);
    action();
    assert.equal(fs.readFileSync(file).equals(before), true, 'I4: a refused callback changed state');
    this.log.push(['refused']);
  }

  // The independent verifier: reads the artifact, never the worker's claim.
  verify(step, attempt, run) {
    const packet = cli.dispatch(this.root, 'packet', run, { attempt }).packet;
    const receipt = cli.dispatch(this.root, 'receipt', run, { attempt });
    const artifact = JSON.parse(fs.readFileSync(receipt.envelope.evidence.path, 'utf8'));
    const passed = receipt.envelope.status === 'SUCCEEDED' && artifact.value === expectedValue(step);
    const outcome = this.outcome(step, reportedAttempts(packet));
    const values = {
      passed,
      reason: passed ? 'value matches' : step + ' ' + outcome + ' rejected by independent check',
      evidence: cli.evidence(this.root, { step, attempt, passed }),
    };
    if (!passed && outcome === 'BLOCKED:replan') values.disposition = 'replan';
    return { values, passed, receipt };
  }
}

// Drive a run with the memoryless driver. Returns the final response.
function drive(root, run, world, amnesia) {
  const entry = [process.execPath, cli.helper, 'next', run];
  let response = cli.argvRun(entry);
  let calls = 1;
  const call = (spec, values, expectFailure) => {
    calls += 1;
    assert.ok(calls < MAX_CALLS, 'driver exceeded ' + MAX_CALLS + ' calls without finishing');
    return cli.runCall(root, spec, values, expectFailure);
  };
  const settle = (response) => {
    if (response.progress && !response.complete) world.oracle.onProgress(response.progress);
    return response;
  };
  // A response without actions (launched, report, retry) hands back next_argv.
  const afterAction = (result) => settle(amnesia || !result.actions ? cli.argvRun(entry) : result);

  let lastSignature = '';
  let repeats = 0;
  while (!response.complete) {
    const actions = response.actions || [];
    // The same actions over and over means the run cannot progress.
    const signature = JSON.stringify([actions.map((item) => [item.action, item.step, item.attempt]),
      (response.active || []).map((item) => item.status)]);
    repeats = signature === lastSignature ? repeats + 1 : 0;
    lastSignature = signature;
    assert.ok(repeats < STALL_LIMIT, 'driver stalled: the same actions repeated ' + STALL_LIMIT + ' times');
    const doable = actions.filter((item) => item.action !== 'replan' && item.action !== 'collect');
    const action = doable[0];
    if (!action) {
      if (actions.some((item) => item.action === 'collect')) {
        const task = world.host.nextToFinish();
        assert.ok(task, 'collect offered but the host has no running task');
        world.workNative(task);
        response = afterAction(call(actions.find((item) => item.action === 'collect').call));
        continue;
      }
      return { response, calls };
    }
    switch (action.action) {
      case 'claim': {
        world.oracle.onClaim(action.call.input.steps);
        const claimed = call(action.call);
        response = afterAction(claimed.next_argv ? cli.argvRun(claimed.next_argv) : claimed);
        break;
      }
      case 'start': {
        const started = call(action.call, world.contextValues(action.step, action.attempt));
        if (amnesia && world.loseContext()) {
          response = settle(cli.argvRun(entry));
          break;
        }
        if (started.action === 'launch') {
          const handle = world.host.launch(started.packet);
          if ((world.faults.lose_launch_response || []).includes(action.step) && !world.lostOnce) {
            world.lostOnce = true;
            response = settle(cli.argvRun(entry));
            break;
          }
          response = afterAction(call(started.call, { handle }));
        } else if (started.action === 'execute') {
          const { status, sha256 } = world.work(started.packet);
          response = afterAction(call(started.call, { status, sha256 }));
        } else {
          response = afterAction(started);
        }
        break;
      }
      case 'reconcile': {
        const task = world.host.lookup(action.attempt);
        if (task) {
          response = afterAction(call(action.call, { handle: task.handle }));
        } else {
          const retried = call(action.retry_call, { reason: 'host confirms it never launched' });
          world.oracle.onRetry(action.step);
          response = afterAction(retried);
        }
        break;
      }
      case 'resume': {
        const packet = cli.dispatch(root, 'packet', run, { attempt: action.attempt }).packet;
        const { status, sha256 } = world.work(packet);
        response = afterAction(call(action.call, { status, sha256 }));
        break;
      }
      case 'verify': {
        const { values, passed, receipt } = world.verify(action.step, action.attempt, run);
        const settled = call(action.call, values);
        world.oracle.onSettle(action.step, receipt.sha256, passed, settled.outcome);
        response = afterAction(settled);
        break;
      }
      case 'retry':
      case 'release': {
        const old = action.action === 'retry' && (world.faults.stale_report || []).includes(action.step)
          ? cli.dispatch(root, 'packet', run, { attempt: action.attempt }).packet : null;
        const retried = call(action.call, { reason: 'scenario retry of ' + action.step });
        world.oracle.onRetry(action.step);
        if (old) {
          // I4: the retired attempt's late report must be refused without effect.
          world.refusedWithoutChange(() => cli.argvRun(old.report_argv, true), run);
        }
        response = afterAction(retried);
        break;
      }
      default:
        throw new Error('driver has no rule for action ' + action.action);
    }
  }
  return { response, calls };
}

// Run one scenario end to end and check its expectations. Returns a summary
// used for the I7 comparison between normal and amnesia runs.
function runScenario(root, scenario, { amnesia = false } = {}) {
  const graph = cli.graphOf(scenario.graph);
  const run = path.join(root, 'runs', crypto.randomUUID());
  fs.mkdirSync(path.dirname(run), { recursive: true });
  const init = { owner: OWNER, graph };
  if (scenario.capacity) init.capacity = scenario.capacity;
  cli.dispatch(root, 'init', run, init);
  const world = new World(root, { ...scenario, graph });
  const { response, calls } = drive(root, run, world, amnesia);
  const expect = scenario.expect || { complete: true };
  // I5: completion is reported exactly when the oracle saw every step accepted.
  assert.equal(response.complete === true, world.oracle.accepted().length === graph.steps.length,
    'I5: complete disagrees with the oracle');
  if (expect.complete) {
    assert.equal(response.complete, true, 'scenario should complete');
  } else {
    assert.equal(response.complete, false);
    assert.match(response.instruction, /cannot complete/);
    assert.deepEqual(response.replan.steps.map((row) => row.step).sort(), [...expect.replan].sort());
  }
  if (expect.accepted) {
    assert.deepEqual(world.oracle.accepted().sort(), [...expect.accepted].sort());
  }
  if (expect.min_refusals) {
    assert.ok(world.log.filter((entry) => entry[0] === 'refused').length >= expect.min_refusals,
      'expected refused stale or duplicate callbacks');
  }
  return {
    calls,
    lost: world.log.filter((entry) => entry[0] === 'lost-context').length,
    accepted: world.oracle.accepted(),
    attempts: Object.fromEntries(world.oracle.attempts),
    replan: response.replan ? response.replan.steps.map((row) => row.step) : [],
  };
}

// A layered random graph with a seeded mix of outcomes; always completable.
function seededScenario(seed) {
  const random = seeded(seed * 7919);
  const layers = 3 + Math.floor(random() * 2);
  const steps = [];
  const outcomes = {};
  let previous = [];
  for (let layer = 0; layer < layers; layer += 1) {
    const width = 2 + Math.floor(random() * 3);
    const current = [];
    for (let index = 0; index < width; index += 1) {
      const id = 'L' + layer + 'N' + index;
      const deps = previous.filter(() => random() < 0.5);
      if (previous.length && deps.length === 0) deps.push(previous[Math.floor(random() * previous.length)]);
      steps.push([id, deps]);
      current.push(id);
      const roll = random();
      if (roll < 0.15) outcomes[id] = ['FAILED', 'SUCCEEDED'];
      else if (roll < 0.25) outcomes[id] = ['FALSE_SUCCESS', 'SUCCEEDED'];
    }
    previous = current;
  }
  steps.push(['JOIN', previous]);
  return {
    id: 'R' + seed,
    name: 'seeded-' + seed,
    graph: steps,
    capacity: 2 + Math.floor(random() * 3),
    schedule: { seed },
    executor: random() < 0.3 ? 'main-context' : 'native',
    outcomes,
    expect: { complete: true },
  };
}

function loadScenarios(dir = path.join(__dirname, 'scenarios')) {
  return fs.readdirSync(dir).filter((name) => name.endsWith('.json')).sort()
    .map((name) => JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8')));
}

module.exports = { runScenario, seededScenario, loadScenarios, Oracle, expectedValue };
