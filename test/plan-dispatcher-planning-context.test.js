'use strict';

// Copied-package coverage for the optional immutable ShipLoop planning context.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'dispatcher-planning-context-')));
const repo = path.resolve(__dirname, '..');
const copied = path.join(root, 'copied-skill');
const unrelated = path.join(root, 'unrelated-cwd');
fs.cpSync(path.join(repo, 'skills/plan-dispatcher'), copied, {recursive: true});
fs.mkdirSync(unrelated);
const helper = path.join(copied, 'scripts/dispatch.js');
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

function save(value, extension = '.json') {
  const file = path.join(root, crypto.randomUUID() + extension);
  fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value));
  return file;
}

function reference(file) {
  return {path: file, sha256: digest(fs.readFileSync(file))};
}

function cli(operation, run, input, fails = false) {
  let inputFile = input === undefined ? undefined : save(input);
  if (operation === 'report') {
    inputFile = path.join(run, 'artifacts', input.attempt, 'envelope.json');
    fs.writeFileSync(inputFile, JSON.stringify(input));
  }
  const child = spawnSync(
    process.execPath,
    [helper, operation, run, ...(inputFile === undefined ? [] : [inputFile])],
    {cwd: unrelated, encoding: 'utf8', timeout: 15000}
  );
  assert.ifError(child.error);
  if (fails) {
    assert.notEqual(child.status, 0, operation + ' unexpectedly succeeded');
    return JSON.parse(child.stderr);
  }
  assert.equal(child.status, 0, child.stderr);
  assert.equal(child.stderr, '');
  return JSON.parse(child.stdout);
}

function capabilities() {
  const child = spawnSync(process.execPath, [helper, 'capabilities'], {
    cwd: unrelated,
    encoding: 'utf8',
    timeout: 15000,
  });
  assert.ifError(child.error);
  assert.equal(child.status, 0, child.stderr);
  return JSON.parse(child.stdout);
}

function contract(id) {
  return {
    task: 'Implement ' + id,
    ready: ['Inputs for ' + id + ' are checked'],
    done: [id + ' is independently checked'],
  };
}

function graph() {
  return {
    version: 1,
    steps: [
      {id: 'B', deps: [], contract: contract('B')},
      {id: 'C', deps: [], contract: contract('C')},
    ],
  };
}

function context(label) {
  const workspace = path.join(root, 'workspace-' + label + '-' + crypto.randomUUID());
  fs.mkdirSync(workspace);
  const readiness = save({label, checked: true});
  return {
    workspace,
    write_scope: ['src/' + label + '.js'],
    resources: [label],
    ready_evidence: reference(readiness),
  };
}

function planningManifest(inputGraph, options = {}) {
  const rawGraph = options.rawGraph || inputGraph;
  const graphFile = save(rawGraph);
  const brief = save('# Consolidated planning brief\n', '.md');
  const b = save('B planning material\n', '.md');
  const c = save('C planning material\n', '.md');
  const artifacts = [
    {
      ...reference(brief),
      roles: ['planning-brief'],
      producers: ['planning-context'],
      classification: 'current',
      required_for: ['*'],
    },
    {
      ...reference(b),
      roles: ['requirements'],
      producers: ['spec-1'],
      classification: 'current',
      required_for: ['B'],
      references: [{action: 'spec-1', index: 0, text: 'B requirement'}],
      origin: reference(b),
      source_reference: 'results/spec-1.md#B',
      display_name: 'B source metadata is preserved',
    },
    {
      ...reference(c),
      roles: ['test-plan'],
      producers: ['test-plan-1'],
      classification: 'current',
      required_for: ['C'],
    },
  ];
  const source = options.source || {
    run_id: 'source-run',
    action_id: 'implement-1',
    workitem: 'item-1',
    revision: 7,
  };
  const manifest = {
    schema: 'shiploop-planning-artifacts/v1',
    source,
    graph: reference(graphFile),
    briefing: reference(brief),
    artifacts,
    unresolved_refs: options.unresolved_refs || [],
    reference_only: options.reference_only || [],
  };
  const manifestFile = save(manifest);
  return {
    planning_context: {
      ...reference(manifestFile),
      source: {run_id: source.run_id, action_id: source.action_id},
    },
    files: {brief, b, c, graphFile, manifestFile},
    manifest,
  };
}

function initialize(inputGraph = graph(), manifest = undefined) {
  const dir = path.join(root, 'run-' + crypto.randomUUID());
  const input = {owner: 'parent', graph: inputGraph};
  if (manifest) input.planning_context = manifest.planning_context;
  return {dir, view: cli('init', dir, input)};
}

function report(run, started, status = 'SUCCEEDED') {
  fs.writeFileSync(started.packet.outputs.artifact, JSON.stringify({actual: 42}));
  return cli('report', run, {
    run_id: started.run_id,
    step: started.step,
    attempt: started.attempt,
    status,
    evidence: reference(started.packet.outputs.artifact),
  });
}

function verification(receipt, passed) {
  const evidenceFile = save({passed});
  return {
    receipt_sha256: receipt.sha256,
    passed,
    reason: passed ? 'Independent result check passed' : 'Independent result check failed',
    evidence: reference(evidenceFile),
  };
}

let count = 0;
let success = false;
function test(name, fn) {
  fn();
  count += 1;
  console.log('PASS ' + name);
}

try {
  test('capabilities advertises the planning-context manifest schema without a run', () => {
    assert.deepEqual(capabilities(), {
      capabilities: {
        planning_context: 'shiploop-planning-artifacts/v1',
        graph_validation: 'execution-graph/v1',
      },
    });
  });

  test('read-only graph preflight matches init validation before any run exists', () => {
    const valid = graph();
    const badDependency = structuredClone(valid);
    badDependency.steps[0].deps = ['MISSING'];
    const cycle = structuredClone(valid);
    cycle.steps[0].deps = ['C'];
    cycle.steps[1].deps = ['B'];
    const emptyDone = structuredClone(valid);
    emptyDone.steps[0].contract.done = [];
    const missingContract = structuredClone(valid);
    delete missingContract.steps[0].contract;
    for (const candidate of [valid, badDependency, cycle, emptyDone, missingContract]) {
      const request = save({graph: candidate});
      const bytes = fs.readFileSync(request);
      const inventory = fs.readdirSync(root, {recursive: true}).sort();
      const result = spawnSync(process.execPath, [helper, 'validate-graph', request], {
        cwd: unrelated, encoding: 'utf8', timeout: 15000,
      });
      assert.ifError(result.error);
      assert.deepEqual(fs.readdirSync(root, {recursive: true}).sort(), inventory);
      assert.deepEqual(fs.readFileSync(request), bytes);
      if (candidate === valid) {
        assert.equal(result.status, 0, result.stderr);
        const checked = JSON.parse(result.stdout);
        assert.deepEqual(checked, {ok: true, graph_sha256: initialize(valid).view.graph_sha256});
      } else {
        assert.notEqual(result.status, 0);
        assert.equal(result.stdout, '');
        const error = JSON.parse(result.stderr).error;
        const absentRun = path.join(root, 'invalid-preflight-' + crypto.randomUUID());
        assert.equal(cli('init', absentRun, {owner: 'parent', graph: candidate}, true).error, error);
        assert.equal(fs.existsSync(absentRun), false);
      }
    }
    const api = require(path.join(copied, 'scripts/dispatch.js'));
    assert.throws(() => api.run('validate-graph', '/unexpected-run', {graph: valid}), /no RUN/);
    assert.throws(() => api.run('validate-graph', undefined, {graph: valid, owner: 'unexpected'}), /expected fields/);
  });

  test('context-bound packets retain step contracts and omit broad graph goals for native and serial starts', () => {
    const inputGraph = graph();
    const broadGoal = 'SENTINEL: never forward this broad planning goal';
    inputGraph.source = {goal: broadGoal};
    const fixture = planningManifest(inputGraph, {rawGraph: inputGraph});
    const {dir, view} = initialize(inputGraph, fixture);
    assert.deepEqual(view.planning_context, fixture.planning_context);
    assert.deepEqual(view.planning_context_check, {ok: true, issues: []});
    assert.deepEqual(view.planning_blocked_steps, []);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, 'plan-dispatcher-state.json'))).version, 2);

    const claimed = cli('claim', dir, {owner: 'parent', steps: ['B', 'C']});
    const b = claimed.claims.find(entry => entry.step === 'B');
    const bPacket = claimed.packets.find(entry => entry.step === 'B');
    assert.deepEqual(bPacket.planning_context, fixture.planning_context);
    assert.deepEqual(bPacket.planning_brief, fixture.manifest.briefing);
    assert.deepEqual(bPacket.reference_material.map(entry => entry.path), [fixture.files.brief, fixture.files.b]);
    assert.equal(bPacket.reference_material[1].source_reference, 'results/spec-1.md#B');
    assert.equal(Object.hasOwn(bPacket, 'planning_context_check'), false);
    assert.match(bPacket.instructions.join(' '), /sole execution assignment.*planning brief.*reference_material/i);
    const assertBoundPacket = (packet, step) => {
      const instructions = packet.instructions.join(' ');
      assert.equal(Object.hasOwn(packet, 'goal'), false);
      assert.equal(JSON.stringify(packet).includes(broadGoal), false);
      assert.equal(packet.task, 'Implement ' + step);
      assert.deepEqual(packet.definition_of_ready, ['Inputs for ' + step + ' are checked']);
      assert.deepEqual(packet.definition_of_done, [step + ' is independently checked']);
      assert.match(instructions,/use applicable planning facts and constraints to carry out this assigned task/i);
      assert.match(instructions,/if they conflict with task, ready, or done.*preserve the discrepancy and report it to the parent before proceeding with affected work/i);
      assert.match(instructions,/do not change the graph/i);
    };
    assertBoundPacket(bPacket, 'B');
    const native = cli('start', dir, {owner: 'parent', attempt: b.attempt, context: context('bound-native')});
    assert.equal(native.action, 'launch');
    assertBoundPacket(native.packet, 'B');
    const serial = cli('start', dir, {
      owner: 'parent',
      attempt: claimed.claims.find(entry => entry.step === 'C').attempt,
      context: context('bound-serial'),
      executor: {kind: 'main-context', id: 'bound-serial-main'},
    });
    assert.equal(serial.action, 'execute');
    assertBoundPacket(serial.packet, 'C');
    assert.deepEqual(cli('check-context', dir, {attempt: b.attempt}).planning_context, fixture.planning_context);
  });

  test('graph-only runs use state version 1 and omit planning-context response fields', () => {
    const inputGraph = graph();
    inputGraph.source = {goal: 'SENTINEL: graph-only goal remains packeted'};
    const {dir, view} = initialize(inputGraph);
    assert.equal(JSON.parse(fs.readFileSync(path.join(dir, 'plan-dispatcher-state.json'))).version, 1);
    assert.equal(Object.hasOwn(view, 'planning_context'), false);
    const claimed = cli('claim', dir, {owner: 'parent', steps: ['B']});
    assert.equal(Object.hasOwn(claimed.packets[0], 'planning_context'), false);
    assert.equal(claimed.packets[0].goal, inputGraph.source.goal);
    assert.deepEqual(cli('check-context', dir, {step: 'B'}).planning_context, null);
  });

  test('init rejects unavailable required planning inputs before creating a run', () => {
    const inputGraph = graph();
    const fixture = planningManifest(inputGraph);
    fs.unlinkSync(fixture.files.b);
    const dir = path.join(root, 'unavailable-' + crypto.randomUUID());
    const failed = cli('init', dir, {
      owner: 'parent', graph: inputGraph, planning_context: fixture.planning_context,
    }, true);
    assert.match(failed.error, /planning context.*unavailable|planning context artifact/i);
    assert.equal(fs.existsSync(dir), false);

    const unresolved = planningManifest(inputGraph, {
      unresolved_refs: [{action: 'spec-1', index: 1, text: 'unresolved B input', required_for: ['B']}],
    });
    const unresolvedDir = path.join(root, 'unresolved-' + crypto.randomUUID());
    assert.match(cli('init', unresolvedDir, {
      owner: 'parent', graph: inputGraph, planning_context: unresolved.planning_context,
    }, true).error, /unresolved required reference/i);
    assert.equal(fs.existsSync(unresolvedDir), false);
  });

  test('unversioned {steps} graph is refused', () => {
    const inputGraph = graph();
    for (const rawGraph of [
      {steps: inputGraph.steps},
      {steps: inputGraph.steps, goal: 'unsupported top-level graph provenance'},
    ]) {
      const incompatible = planningManifest(inputGraph, {rawGraph});
      const dir = path.join(root, 'bad-graph-' + crypto.randomUUID());
      assert.match(cli('init', dir, {
        owner: 'parent', graph: inputGraph, planning_context: incompatible.planning_context,
      }, true).error, /graph.*unexpected fields/i);
      assert.equal(fs.existsSync(dir), false);
    }
  });

  test('a step-specific artifact drift is visible, checkable, and blocks only its fresh start', () => {
    const inputGraph = graph();
    const fixture = planningManifest(inputGraph);
    const {dir} = initialize(inputGraph, fixture);
    const claimed = cli('claim', dir, {owner: 'parent', steps: ['B', 'C']});
    const b = claimed.claims.find(entry => entry.step === 'B');
    const c = claimed.claims.find(entry => entry.step === 'C');
    const before = fs.readFileSync(path.join(dir, 'plan-dispatcher-state.json'));
    fs.writeFileSync(fixture.files.b, 'changed B planning material\n');

    const view = cli('next', dir);
    assert.deepEqual(view.planning_blocked_steps, ['B']);
    assert.equal(view.planning_context_check.ok, false);
    assert.deepEqual(cli('check-context', dir, {step: 'B'}).ok, false);
    assert.deepEqual(cli('check-context', dir, {step: 'C'}).ok, true);
    assert.equal(view.actions.find(entry => entry.attempt === b.attempt).action, 'inspect-planning-context');
    assert.equal(view.actions.find(entry => entry.attempt === b.attempt).recovery, 'start');

    const packet = cli('packet', dir, {attempt: b.attempt}).packet;
    assert.deepEqual(packet.planning_context, fixture.planning_context);
    assert.deepEqual(packet.planning_brief, fixture.manifest.briefing);
    assert.equal(Object.hasOwn(packet, 'planning_context_check'), false);
    assert.match(cli('start', dir, {owner: 'parent', attempt: b.attempt, context: context('blocked-b')}, true).error, /planning context.*unavailable/i);
    assert.deepEqual(fs.readFileSync(path.join(dir, 'plan-dispatcher-state.json')), before);
    assert.equal(fs.existsSync(path.join(dir, 'artifacts', b.attempt)), false);
    assert.equal(cli('start', dir, {owner: 'parent', attempt: c.attempt, context: context('open-c')}).action, 'launch');
  });

  test('drift never blocks report, receipt, negative settlement, retry, or takeover, but blocks acceptance', () => {
    const inputGraph = graph();
    const fixture = planningManifest(inputGraph);
    const {dir} = initialize(inputGraph, fixture);
    const claim = cli('claim', dir, {owner: 'parent', steps: ['B']}).claims[0];
    const started = cli('start', dir, {owner: 'parent', attempt: claim.attempt, context: context('settlement-b')});
    cli('launched', dir, {owner: 'parent', attempt: claim.attempt, handle: 'fixture-handle'});
    fs.writeFileSync(fixture.files.b, 'changed after start\n');
    const receipt = report(dir, started);
    assert.deepEqual(cli('receipt', dir, {attempt: claim.attempt}).sha256, receipt.sha256);
    const beforePositive = fs.readFileSync(path.join(dir, 'plan-dispatcher-state.json'));
    assert.match(cli('settle', dir, {
      owner: 'parent', attempt: claim.attempt, verification: verification(receipt, true),
    }, true).error, /planning context.*unavailable/i);
    assert.deepEqual(fs.readFileSync(path.join(dir, 'plan-dispatcher-state.json')), beforePositive);

    const rejected = cli('settle', dir, {
      owner: 'parent', attempt: claim.attempt, verification: verification(receipt, false),
    });
    assert.equal(rejected.outcome, 'rejected');
    assert.equal(cli('retry', dir, {
      owner: 'parent', attempt: claim.attempt, confirmed_stopped: true, reason: 'fixture stopped',
    }).retry.status, 'retried');
    assert.equal(cli('takeover', dir, {
      oldOwner: 'parent', newOwner: 'parent-2', confirmed_stopped: true, reason: 'fixture parent handoff',
    }).owner, 'parent-2');
  });

  success = true;
  console.log(`plan-dispatcher-planning-context.test.js: ${count} groups passed (copied package, no native agents)`);
} finally {
  if (success) fs.rmSync(root, {recursive: true, force: true});
  else console.error('Retained failed planning-context fixtures: ' + root);
}
