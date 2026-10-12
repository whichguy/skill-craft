'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {after, test} = require('node:test');

const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'dispatcher-harness-')));
const repo = path.resolve(__dirname, '..');
const copied = path.join(root, 'copied-skill');
const unrelated = path.join(root, 'unrelated-cwd');
fs.cpSync(path.join(repo, 'skills/plan-dispatcher'), copied, {recursive: true});
fs.mkdirSync(unrelated);
const helper = path.join(copied, 'scripts/dispatch.js');
const STATE_FILE = 'plan-dispatcher-state.json';
const marker = {schema: 'agent-harness/v1', ask_agent_interface: 'compact'};
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const save = value => {
  const file = path.join(root, crypto.randomUUID() + '.json');
  fs.writeFileSync(file, JSON.stringify(value));
  return file;
};
const evidence = value => {
  const file = save(value);
  return {path: file, sha256: digest(fs.readFileSync(file))};
};

function cli(op, run, input, fails = false) {
  let inputFile;
  if (input !== undefined) {
    inputFile = op === 'report'
      ? path.join(run, 'artifacts', input.attempt, 'envelope.json')
      : save(input);
    if (op === 'report') fs.writeFileSync(inputFile, JSON.stringify(input));
  }
  const child = spawnSync(process.execPath, [helper, op, run, ...(inputFile === undefined ? [] : [inputFile])],
    {cwd: unrelated, encoding: 'utf8', timeout: 15000});
  assert.ifError(child.error);
  if (fails) {
    assert.notEqual(child.status, 0);
    return JSON.parse(child.stderr);
  }
  assert.equal(child.status, 0, child.stderr);
  assert.equal(child.stderr, '');
  return JSON.parse(child.stdout);
}

const contract = id => ({task: `Implement ${id}`, ready: [`Inputs for ${id} verified`], done: [`${id} independently checked`]});
function graph(ids, profile = false) {
  const result = {version: 1, steps: ids.map(id => ({id, deps: [], contract: contract(id)}))};
  if (profile) result.source = {agent_harness: {...marker}};
  return result;
}
function initialize(ids, profile = false) {
  const dir = path.join(root, crypto.randomUUID());
  const result = cli('init', dir, {owner: 'coordinator', graph: graph(ids, profile)});
  return {dir, result};
}
function makeWorkspace() {
  const workspace = path.join(root, crypto.randomUUID());
  fs.mkdirSync(workspace);
  return workspace;
}
function context(workspace, overrides = {}) {
  return {
    workspace,
    write_scope: ['src/result.js'],
    resources: [],
    ready_evidence: evidence({ready: true}),
    ...overrides,
  };
}
function readOnlyContext(workspace, overrides = {}) {
  return context(workspace, {read_only: true, write_scope: [], ...overrides});
}
function claim(dir, step) {
  const response = cli('claim', dir, {owner: 'coordinator', steps: [step]});
  return {response, attempt: response.claims[0].attempt};
}
function state(dir) {
  return JSON.parse(fs.readFileSync(path.join(dir, STATE_FILE), 'utf8'));
}

after(() => fs.rmSync(root, {recursive: true, force: true}));

test('three active read-only attempts may share one canonical workspace', () => {
  const {dir} = initialize(['A', 'B', 'C']);
  const workspace = makeWorkspace();
  for (const step of ['A', 'B', 'C']) {
    const {attempt} = claim(dir, step);
    const started = cli('start', dir, {owner: 'coordinator', attempt, context: readOnlyContext(workspace)});
    assert.equal(started.action, 'launch');
  }
  const attempts = Object.values(state(dir).attempts);
  assert.equal(attempts.length, 3);
  assert.deepEqual(attempts.map(item => item.context), attempts.map(item => ({
    workspace: fs.realpathSync(workspace),
    write_scope: [],
    resources: [],
    read_only: true,
    ready_evidence: item.context.ready_evidence,
  })));
});

test('shared read-only workspaces still reject external resource collisions', () => {
  const {dir} = initialize(['A', 'B']);
  const workspace = makeWorkspace();
  const {attempt: first} = claim(dir, 'A');
  cli('start', dir, {owner: 'coordinator', attempt: first,
    context: readOnlyContext(workspace, {resources: ['database:shared']})});
  const {attempt: second} = claim(dir, 'B');
  const failed = cli('start', dir, {owner: 'coordinator', attempt: second,
    context: readOnlyContext(workspace, {resources: ['database:shared']})}, true);
  assert.match(failed.error, /resource.*already reserved/i);
});

test('a read-only reservation cannot overlap a writer in the same workspace', () => {
  const {dir} = initialize(['A', 'B']);
  const workspace = makeWorkspace();
  const {attempt: reader} = claim(dir, 'A');
  cli('start', dir, {owner: 'coordinator', attempt: reader, context: readOnlyContext(workspace)});
  const {attempt: writer} = claim(dir, 'B');
  const failed = cli('start', dir, {owner: 'coordinator', attempt: writer,
    context: context(workspace)}, true);
  assert.match(failed.error, /workspace overlaps/i);
  assert.equal(state(dir).attempts[writer].status, 'claimed');
  assert.equal(Object.hasOwn(state(dir).attempts[writer], 'context'), false);
});

test('read-only sharing rejects related but nonidentical canonical directories', () => {
  const {dir} = initialize(['A', 'B']);
  const parent = makeWorkspace();
  const nested = path.join(parent, 'nested');
  fs.mkdirSync(nested);
  const {attempt: first} = claim(dir, 'A');
  cli('start', dir, {owner: 'coordinator', attempt: first, context: readOnlyContext(parent)});
  const {attempt: second} = claim(dir, 'B');
  const failed = cli('start', dir, {owner: 'coordinator', attempt: second, context: readOnlyContext(nested)}, true);
  assert.match(failed.error, /workspace overlaps/i);
});

test('read_only must be boolean and only true permits an empty scope', () => {
  const {dir} = initialize(['A', 'B', 'C', 'D']);
  const workspace = makeWorkspace();
  const invalid = [
    {read_only: 'true', write_scope: []},
    {read_only: true, write_scope: ['src/read.js']},
    {read_only: false, write_scope: []},
    {write_scope: []},
  ];
  for (let index = 0; index < invalid.length; index += 1) {
    const step = ['A', 'B', 'C', 'D'][index];
    const {attempt} = claim(dir, step);
    const failed = cli('start', dir, {owner: 'coordinator', attempt,
      context: context(workspace, invalid[index])}, true);
    assert.match(failed.error, index === 0 ? /read_only must be a boolean/i : /write_scope/i);
    assert.equal(Object.hasOwn(state(dir).attempts[attempt], 'context'), false);
  }
});

test('read_only survives cold recovery without authorizing a duplicate launch', () => {
  const {dir} = initialize(['A'], true);
  const workspace = makeWorkspace();
  const {attempt} = claim(dir, 'A');
  const assigned = readOnlyContext(workspace);
  const started = cli('start', dir, {owner: 'coordinator', attempt, context: assigned});
  assert.equal(started.action, 'launch');
  assert.equal(started.packet.context.read_only, true);
  assert.equal(started.packet.context.write_scope.length, 0);

  const beforeReplay = fs.readFileSync(path.join(dir, STATE_FILE));
  const replay = cli('start', dir, {owner: 'coordinator', attempt, context: assigned});
  assert.equal(replay.action, 'reconcile');
  assert.deepEqual(fs.readFileSync(path.join(dir, STATE_FILE)), beforeReplay);
  const recovered = cli('next', dir);
  assert.equal(recovered.actions.find(action => action.attempt === attempt).action, 'reconcile');
  assert.match(recovered.actions.find(action => action.attempt === attempt).instruction, /never repeat prepare or launch/i);
  assert.match(recovered.instruction, /coordinator owns this fresh Dispatcher run from init/i);

  const launched = cli('launched', dir, {owner: 'coordinator', attempt, handle: 'native-task-A'});
  assert.match(launched.instruction, /do not repeat preparation/i);
  const collecting = cli('next', dir);
  const collect = collecting.actions.find(action => action.attempt === attempt);
  assert.equal(collect.action, 'collect');
  assert.match(collect.instruction, /verify-return/i);
  assert.match(collect.instruction, /coordinator then writes the Dispatcher result artifact and envelope/i);

  fs.writeFileSync(started.packet.outputs.artifact, JSON.stringify({result: 'worker returned'}));
  const envelope = {
    ...started.packet.report_envelope,
    status: 'SUCCEEDED',
    evidence: {path: started.packet.outputs.artifact, sha256: digest(fs.readFileSync(started.packet.outputs.artifact))},
  };
  const report = cli('report', dir, envelope);
  assert.match(report.instruction, /receipt published by the coordinator/i);
  const verifying = cli('next', dir);
  const verify = verifying.actions.find(action => action.attempt === attempt);
  assert.equal(verify.action, 'verify');
  assert.match(verify.instruction, /compact verify-return evidence/i);
});

test('exact agent_harness marker selects compact guidance and default graphs retain legacy guidance', () => {
  const compact = initialize(['A'], true);
  assert.match(compact.result.instruction, /coordinator owns this fresh Dispatcher run from init/i);
  const prepared = claim(compact.dir, 'A').response;
  assert.match(prepared.instruction, /compact Ask-Agent task packet/i);
  assert.doesNotMatch(prepared.instruction, /capabilities --skill-card ABS|ask_agent_workspace\.py prepare|inspect --phase prepared/i);
  assert.match(prepared.packets[0].instructions.join(' '), /worker-start.*worker-finish/i);
  assert.match(prepared.packets[0].instructions.join(' '), /verify-return/i);
  const workerInstructions = prepared.packets[0].instructions.join(' ');
  assert.match(workerInstructions, /Do not ask the worker to write Dispatcher artifacts or execute report_argv/i);
  assert.doesNotMatch(workerInstructions, /Execute report_argv without shell interpolation/i);
  const startInput = prepared.calls[0].call.input;
  assert.equal(startInput.context.read_only, '<omit unless true for a read-only task>');
  assert.equal(startInput.context.write_scope, '<relative path array; use [] only when read_only is true>');

  const defaultRun = initialize(['A']);
  assert.match(defaultRun.result.instruction, /The main conversation owns this run/i);
  const defaultClaimed = claim(defaultRun.dir, 'A');
  const defaultClaim = defaultClaimed.response;
  assert.match(defaultClaim.instruction, /capabilities --skill-card ABS/i);
  assert.match(defaultClaim.packets[0].instructions.join(' '), /check-context --receipt/i);
  assert.doesNotMatch(defaultClaim.packets[0].instructions.join(' '), /compact Ask-Agent task package/i);
  const defaultStart = defaultClaim.calls[0].call.input;
  assert.deepEqual(Object.keys(defaultStart.context).sort(), ['ready_evidence', 'resources', 'workspace', 'write_scope']);
  cli('start', defaultRun.dir, {owner: 'coordinator', attempt: defaultClaimed.attempt,
    context: context(makeWorkspace())});
  assert.equal(Object.hasOwn(state(defaultRun.dir).attempts[defaultClaimed.attempt].context, 'read_only'), false);

  const mismatchedGraph = graph(['A']);
  mismatchedGraph.source = {agent_harness: {...marker, extra: true}};
  const mismatchedDir = path.join(root, crypto.randomUUID());
  const mismatched = cli('init', mismatchedDir, {owner: 'coordinator', graph: mismatchedGraph});
  assert.match(mismatched.instruction, /The main conversation owns this run/i);
});
