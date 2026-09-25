'use strict';

/*
 * Public copied-package coverage for the dispatcher progress projection.
 * The simulated workers only publish durable result envelopes through the
 * documented CLI; no agent or model is launched by this test.
 */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const repo = path.resolve(__dirname, '..');
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'dispatcher-progress-')));
const copied = path.join(root, 'copied-skill');
const unrelated = path.join(root, 'unrelated-cwd');
fs.cpSync(path.join(repo, 'skills/plan-dispatcher'), copied, {recursive: true});
fs.mkdirSync(unrelated);
const helper = path.join(copied, 'scripts/dispatch.js');
const STATE_FILE = 'plan-dispatcher-state.json';
const CATEGORIES = [
  'completed', 'active', 'awaiting_verification', 'pending', 'blocked', 'failed',
];
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

function save(value, extension = '.json') {
  const file = path.join(root, crypto.randomUUID() + extension);
  fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value));
  return file;
}

function reference(file) {
  return {path: file, sha256: digest(fs.readFileSync(file))};
}

function cli(operation, run, input, fails = false) {
  let inputFile;
  if (input !== undefined) {
    inputFile = operation === 'report'
      ? path.join(run, 'artifacts', input.attempt, 'envelope.json')
      : save(input);
    if (operation === 'report') {
      fs.writeFileSync(inputFile, JSON.stringify(input));
    }
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

function contract(id) {
  return {
    task: 'Deliver task ' + id,
    ready: ['Inputs for ' + id + ' are verified'],
    done: ['Task ' + id + ' is independently verified'],
  };
}

function lifecycleGraph() {
  return {
    version: 1,
    steps: [
      {id: 'A', deps: [], contract: contract('A')},
      {id: 'B', deps: ['A'], contract: contract('B')},
      {id: 'D', deps: ['B'], contract: contract('D')},
      {id: 'C', deps: [], contract: contract('C')},
    ],
  };
}

function planningGraph() {
  return {
    version: 1,
    steps: [
      {id: 'A', deps: [], contract: contract('A')},
      {id: 'B', deps: ['A'], contract: contract('B')},
      {id: 'C', deps: [], contract: contract('C')},
    ],
  };
}

function singleGraph() {
  return {
    version: 1,
    steps: [{id: 'A', deps: [], contract: contract('A')}],
  };
}

function initialize(graph = lifecycleGraph(), planning = undefined) {
  const dir = path.join(root, 'run-' + crypto.randomUUID());
  const input = {owner: 'parent', graph};
  if (planning) {
    input.planning_context = planning.planning_context;
  }
  return {dir, response: cli('init', dir, input)};
}

function context(label) {
  const workspace = path.join(root, 'workspace-' + label + '-' + crypto.randomUUID());
  fs.mkdirSync(workspace);
  const readiness = save({label, ready: true});
  return {
    workspace,
    write_scope: ['src/' + label + '.js'],
    resources: [],
    ready_evidence: reference(readiness),
  };
}

function verification(receipt, passed, reason) {
  const evidence = save({passed, reason});
  return {
    receipt_sha256: receipt.sha256,
    passed,
    reason,
    evidence: reference(evidence),
  };
}

function publish(run, started, status) {
  fs.writeFileSync(started.packet.outputs.artifact, JSON.stringify({
    fixture: 'public-cli progress coverage',
    step: started.step,
    attempt: started.attempt,
    status,
  }));
  const envelope = {
    run_id: started.run_id,
    step: started.step,
    attempt: started.attempt,
    status,
    evidence: reference(started.packet.outputs.artifact),
  };
  const report = cli('report', run, envelope);
  const receipt = cli('receipt', run, {attempt: started.attempt});
  return {envelope, report, receipt};
}

function stateBytes(run) {
  return fs.readFileSync(path.join(run, STATE_FILE));
}

function rows(progress) {
  return CATEGORIES.flatMap((category) => progress[category].map((row) => ({category, row})));
}

function row(progress, category, step) {
  const matches = progress[category].filter((entry) => entry.step === step);
  assert.equal(matches.length, 1, step + ' should occur once in ' + category);
  return matches[0];
}

function assertProgress(progress, graph) {
  assert.deepEqual(Object.keys(progress).sort(), [...CATEGORIES, 'counts'].sort());
  for (const category of CATEGORIES) {
    assert.ok(Array.isArray(progress[category]), category + ' is an array');
  }
  assert.deepEqual(Object.keys(progress.counts).sort(), [
    'total', 'remaining', ...CATEGORIES,
  ].sort());

  const graphByStep = new Map(graph.steps.map((step) => [step.id, step]));
  const allRows = rows(progress);
  assert.equal(allRows.length, graph.steps.length, 'every graph task has one progress row');
  assert.deepEqual(
    allRows.map((entry) => entry.row.step).sort(),
    graph.steps.map((step) => step.id).sort(),
    'progress rows cover the frozen graph exactly once'
  );
  assert.equal(new Set(allRows.map((entry) => entry.row.step)).size, graph.steps.length);

  for (const {category, row: entry} of allRows) {
    const step = graphByStep.get(entry.step);
    assert.ok(step, 'progress row references a graph step');
    assert.equal(entry.task, step.contract.task, entry.step + ' preserves contract.task');
    assert.equal(typeof entry.state, 'string');
    assert.ok(entry.state.length > 0);
    assert.ok(Array.isArray(entry.unmet_dependencies));
    assert.equal(typeof entry.reason, 'string');
    assert.ok(entry.reason.length > 0);
    if (category === 'pending') {
      assert.equal(typeof entry.dependency_ready, 'boolean');
    } else {
      assert.equal(Object.hasOwn(entry, 'dependency_ready'), false);
    }
    if (category === 'awaiting_verification') {
      assert.ok(['SUCCEEDED', 'FAILED', 'BLOCKED'].includes(entry.reported_status));
    } else {
      assert.equal(Object.hasOwn(entry, 'reported_status'), false);
    }
    if (Object.hasOwn(entry, 'attempt')) {
      assert.equal(typeof entry.attempt, 'string');
      assert.ok(entry.attempt.length > 0);
    }
    if (Object.hasOwn(entry, 'planning_issues')) {
      assert.ok(Array.isArray(entry.planning_issues));
      assert.ok(entry.planning_issues.length > 0);
      for (const issue of entry.planning_issues) {
        assert.ok(issue.required_for.includes('*') || issue.required_for.includes(entry.step),
          'planning issue is scoped to its own step or all steps');
      }
    }
  }

  for (const category of CATEGORIES) {
    assert.equal(progress.counts[category], progress[category].length,
      'count for ' + category + ' matches its rows');
  }
  assert.equal(progress.counts.total, graph.steps.length);
  assert.equal(
    progress.counts.remaining,
    progress.counts.active + progress.counts.awaiting_verification +
      progress.counts.pending + progress.counts.blocked + progress.counts.failed,
    'remaining includes every noncompleted category'
  );
  assert.equal(progress.counts.remaining, progress.counts.total - progress.counts.completed);
}

function assertProgressResponse(response, graph) {
  assert.ok(Object.hasOwn(response, 'progress'), 'parent response includes progress');
  assertProgress(response.progress, graph);
  assert.deepEqual(response.next_argv, [process.execPath, helper, 'next', response.next_argv[3]]);
  return response.progress;
}

function assertReceiptOnly(response, kind) {
  assert.equal(Object.hasOwn(response, 'progress'), false, kind + ' remains receipt-only');
  assert.equal(typeof response.sha256, 'string');
  assert.ok(response.sha256.length > 0);
  assert.equal(typeof response.instruction, 'string');
}

function assertReadOnlyNext(run, graph) {
  const before = stateBytes(run);
  const revision = JSON.parse(before).revision;
  const first = cli('next', run);
  const middle = stateBytes(run);
  const second = cli('next', run);
  assertProgressResponse(first, graph);
  assertProgressResponse(second, graph);
  assert.deepEqual(middle, before, 'first cold next does not rewrite state');
  assert.deepEqual(stateBytes(run), before, 'repeated cold next does not rewrite state');
  assert.equal(first.revision, revision);
  assert.equal(second.revision, revision);
  assert.deepEqual(first.progress, second.progress, 'cold reads have a stable progress projection');
}

/* A minimal valid ShipLoop planning manifest used only by this test. */
function planningManifest(graph) {
  const graphFile = save(graph);
  const brief = save('# Planning brief\n', '.md');
  const aMaterial = save('A-specific planning input\n', '.md');
  const manifest = {
    schema: 'shiploop-planning-artifacts/v1',
    source: {run_id: 'source-run', action_id: 'plan-action', workitem: 'item-1', revision: 1},
    graph: reference(graphFile),
    briefing: reference(brief),
    artifacts: [
      {
        ...reference(brief),
        roles: ['planning-brief'],
        producers: ['planner'],
        classification: 'current',
        required_for: ['*'],
      },
      {
        ...reference(aMaterial),
        roles: ['requirements'],
        producers: ['planner'],
        classification: 'current',
        required_for: ['A'],
      },
    ],
    unresolved_refs: [],
    reference_only: [],
  };
  const manifestFile = save(manifest);
  return {
    planning_context: {
      ...reference(manifestFile),
      source: {run_id: 'source-run', action_id: 'plan-action'},
    },
    aMaterial,
    originalA: fs.readFileSync(aMaterial),
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
  test('initial and read-only progress partition the frozen graph without granting launches', () => {
    const graph = lifecycleGraph();
    const {dir, response} = initialize(graph);
    const progress = assertProgressResponse(response, graph);
    assert.deepEqual(response.ready, ['A', 'C']);
    assert.deepEqual(response.active, []);
    assert.deepEqual(response.accepted, []);
    assert.equal(response.complete, false);
    assert.ok(response.actions.some((action) => action.action === 'claim'));

    const a = row(progress, 'pending', 'A');
    const b = row(progress, 'pending', 'B');
    const d = row(progress, 'pending', 'D');
    const c = row(progress, 'pending', 'C');
    assert.equal(a.state, 'pending');
    assert.deepEqual(a.unmet_dependencies, []);
    assert.equal(a.dependency_ready, true);
    assert.equal(b.dependency_ready, false);
    assert.deepEqual(b.unmet_dependencies, ['A']);
    assert.equal(d.dependency_ready, false);
    assert.deepEqual(d.unmet_dependencies, ['B']);
    assert.equal(c.dependency_ready, true);
    assert.equal(progress.counts.remaining, 4);

    assertReadOnlyNext(dir, graph);
  });

  test('progress follows claim through receipts, verified acceptance, rejection, retry, and all report statuses', () => {
    const graph = lifecycleGraph();
    const {dir} = initialize(graph);
    let owner = 'parent';

    const claimed = cli('claim', dir, {owner, steps: ['A']});
    let progress = assertProgressResponse(claimed, graph);
    const aClaim = claimed.claims[0];
    const activeClaim = row(progress, 'active', 'A');
    assert.equal(activeClaim.state, 'claimed');
    assert.equal(activeClaim.attempt, aClaim.attempt);
    assert.equal(row(progress, 'pending', 'B').dependency_ready, false);

    const taken = cli('takeover', dir, {
      oldOwner: owner,
      newOwner: 'parent-2',
      confirmed_stopped: true,
      reason: 'fixture owner transition',
    });
    owner = 'parent-2';
    progress = assertProgressResponse(taken, graph);
    assert.equal(taken.owner, owner);
    assert.equal(row(progress, 'active', 'A').state, 'claimed');

    const startedA = cli('start', dir, {owner, attempt: aClaim.attempt, context: context('A')});
    progress = assertProgressResponse(startedA, graph);
    assert.equal(row(progress, 'active', 'A').state, 'launching');

    // A successful report before launch confirmation is still only an inbox
    // receipt. It remains unaccepted and requires native reconciliation.
    const aPublication = publish(dir, startedA, 'SUCCEEDED');
    assertReceiptOnly(aPublication.report, 'report');
    assertReceiptOnly(aPublication.receipt, 'receipt');
    assert.match(aPublication.report.instruction, /return this exact response.*parent dispatcher/i);
    assert.match(aPublication.report.instruction, /do not execute next_argv/i);
    let next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    const awaitingA = row(progress, 'awaiting_verification', 'A');
    assert.equal(awaitingA.state, 'receipt');
    assert.equal(awaitingA.attempt, aClaim.attempt);
    assert.equal(awaitingA.reported_status, 'SUCCEEDED');
    assert.equal(next.complete, false);
    assert.equal(next.active.find((entry) => entry.step === 'A').recovery, 'reconcile');

    const launchedA = cli('launched', dir, {owner, attempt: aClaim.attempt, handle: 'fixture-A'});
    progress = assertProgressResponse(launchedA, graph);
    assert.equal(row(progress, 'awaiting_verification', 'A').reported_status, 'SUCCEEDED');

    const accepted = cli('settle', dir, {
      owner,
      attempt: aClaim.attempt,
      verification: verification(aPublication.receipt, true, 'A fixture independently accepted'),
    });
    progress = assertProgressResponse(accepted, graph);
    const acceptedA = row(progress, 'completed', 'A');
    assert.equal(acceptedA.state, 'accepted');
    assert.equal(acceptedA.attempt, aClaim.attempt);
    assert.equal(row(progress, 'pending', 'B').dependency_ready, true);
    assert.deepEqual(accepted.accepted, ['A']);
    assert.deepEqual(accepted.ready, ['B', 'C']);
    assert.equal(accepted.complete, false);
    assert.ok(accepted.actions.some((action) => action.action === 'claim' && action.steps.includes('B')));
    assert.equal(accepted.actions.some((action) => action.step === 'B' && action.action === 'start'), false,
      'dependency_ready advertises structural eligibility, not a launch grant');

    const claimedB = cli('claim', dir, {owner, steps: ['B']});
    progress = assertProgressResponse(claimedB, graph);
    const bClaim = claimedB.claims[0];
    assert.equal(row(progress, 'active', 'B').state, 'claimed');
    const startedB = cli('start', dir, {owner, attempt: bClaim.attempt, context: context('B')});
    assertProgressResponse(startedB, graph);
    const launchedB = cli('launched', dir, {owner, attempt: bClaim.attempt, handle: 'fixture-B'});
    assertProgressResponse(launchedB, graph);
    const bPublication = publish(dir, startedB, 'FAILED');
    assertReceiptOnly(bPublication.report, 'failed report');
    assertReceiptOnly(bPublication.receipt, 'failed receipt');
    next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    assert.equal(row(progress, 'awaiting_verification', 'B').reported_status, 'FAILED');
    assert.equal(next.complete, false);

    const rejected = cli('settle', dir, {
      owner,
      attempt: bClaim.attempt,
      verification: verification(bPublication.receipt, false, 'B fixture verifier rejected the result'),
    });
    progress = assertProgressResponse(rejected, graph);
    const failedB = row(progress, 'failed', 'B');
    assert.equal(failedB.state, 'rejected');
    assert.equal(failedB.attempt, bClaim.attempt);
    assert.match(failedB.reason, /B fixture verifier rejected/i);
    const blockedD = row(progress, 'blocked', 'D');
    assert.equal(blockedD.state, 'blocked');
    assert.deepEqual(blockedD.unmet_dependencies, ['B']);
    assert.deepEqual(blockedD.blocked_dependencies, ['B']);
    assert.equal(rejected.complete, false);

    const retried = cli('retry', dir, {
      owner,
      attempt: bClaim.attempt,
      confirmed_stopped: true,
      reason: 'fixture B worker stopped',
    });
    progress = assertProgressResponse(retried, graph);
    assert.equal(progress.failed.some((entry) => entry.step === 'B'), false);
    assert.equal(progress.blocked.some((entry) => entry.step === 'D'), false);
    const retriedB = row(progress, 'pending', 'B');
    assert.equal(retriedB.state, 'pending');
    assert.equal(retriedB.dependency_ready, true);
    assert.equal(row(progress, 'pending', 'D').dependency_ready, false);

    // C remains a disconnected unfinished task, so a BLOCKED report also
    // remains awaiting verification and cannot make the whole run complete.
    const claimedC = cli('claim', dir, {owner, steps: ['C']});
    progress = assertProgressResponse(claimedC, graph);
    const cClaim = claimedC.claims[0];
    const startedC = cli('start', dir, {owner, attempt: cClaim.attempt, context: context('C')});
    assertProgressResponse(startedC, graph);
    const launchedC = cli('launched', dir, {owner, attempt: cClaim.attempt, handle: 'fixture-C'});
    assertProgressResponse(launchedC, graph);
    const cPublication = publish(dir, startedC, 'BLOCKED');
    assertReceiptOnly(cPublication.report, 'blocked report');
    assertReceiptOnly(cPublication.receipt, 'blocked receipt');
    next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    assert.equal(row(progress, 'awaiting_verification', 'C').state, 'receipt');
    assert.equal(row(progress, 'awaiting_verification', 'C').reported_status, 'BLOCKED');
    assert.equal(next.complete, false);
    assert.equal(progress.counts.total, 4);
    assert.equal(progress.counts.completed, 1);
    assert.equal(progress.counts.remaining, 3);
  });

  test('a main-context receipt awaits parent verification without native reconciliation', () => {
    const graph = singleGraph();
    const {dir} = initialize(graph);
    const claimed = cli('claim', dir, {owner: 'parent', steps: ['A']});
    const aClaim = claimed.claims[0];
    const started = cli('start', dir, {
      owner: 'parent',
      attempt: aClaim.attempt,
      context: context('main-context-A'),
      executor: {kind: 'main-context', id: 'fixture-main-context'},
    });
    let progress = assertProgressResponse(started, graph);
    assert.equal(started.action, 'execute');
    assert.equal(row(progress, 'active', 'A').state, 'running');

    const publication = publish(dir, started, 'SUCCEEDED');
    assertReceiptOnly(publication.report, 'main-context report');
    assertReceiptOnly(publication.receipt, 'main-context receipt');
    const next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    const awaiting = row(progress, 'awaiting_verification', 'A');
    assert.equal(awaiting.state, 'receipt');
    assert.equal(awaiting.reported_status, 'SUCCEEDED');
    assert.doesNotMatch(awaiting.reason, /reconciliation is required/i);
    assert.equal(next.active.find((entry) => entry.step === 'A').recovery, 'verify');
    assert.equal(next.actions.some((action) => action.step === 'A' && action.action === 'reconcile'), false);
    assert.equal(next.complete, false);

    const settled = cli('settle', dir, {
      owner: 'parent',
      attempt: aClaim.attempt,
      verification: verification(publication.receipt, true, 'main-context fixture accepted'),
    });
    progress = assertProgressResponse(settled, graph);
    assert.equal(settled.complete, true);
    assert.equal(progress.counts.total, 1);
    assert.equal(progress.counts.remaining, 0);
    assert.equal(progress.counts.completed, 1);
    assert.equal(row(progress, 'completed', 'A').state, 'accepted');
    for (const category of CATEGORIES.filter((category) => category !== 'completed')) {
      assert.deepEqual(progress[category], []);
    }
  });

  test('planning faults stay scoped while lifecycle categories retain their durable state', () => {
    const graph = planningGraph();
    const fixture = planningManifest(graph);
    const {dir} = initialize(graph, fixture);
    const issueRows = (progress) => rows(progress).filter((entry) => Object.hasOwn(entry.row, 'planning_issues'));
    const assertOnlyAHasIssues = (progress) => {
      const affected = issueRows(progress);
      assert.equal(affected.length, 1);
      assert.equal(affected[0].row.step, 'A');
      assert.equal(affected[0].row.planning_issues[0].required_for.includes('A'), true);
      for (const step of ['B', 'C']) {
        const entry = rows(progress).find((candidate) => candidate.row.step === step).row;
        assert.equal(Object.hasOwn(entry, 'planning_issues'), false, step + ' has no unrelated global issue');
      }
    };

    fs.writeFileSync(fixture.aMaterial, 'missing A planning input\n');
    let next = cli('next', dir);
    let progress = assertProgressResponse(next, graph);
    const pendingBlockedA = row(progress, 'blocked', 'A');
    assert.equal(pendingBlockedA.state, 'pending');
    assert.equal(Object.hasOwn(pendingBlockedA, 'attempt'), false);
    assertOnlyAHasIssues(progress);
    assert.equal(row(progress, 'pending', 'B').dependency_ready, false);
    assert.equal(row(progress, 'pending', 'C').dependency_ready, true);

    fs.writeFileSync(fixture.aMaterial, fixture.originalA);
    const claim = cli('claim', dir, {owner: 'parent', steps: ['A']});
    assertProgressResponse(claim, graph);
    const aClaim = claim.claims[0];
    fs.writeFileSync(fixture.aMaterial, 'changed after claim\n');
    next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    const claimedBlockedA = row(progress, 'blocked', 'A');
    assert.equal(claimedBlockedA.state, 'claimed');
    assert.equal(claimedBlockedA.attempt, aClaim.attempt);
    assertOnlyAHasIssues(progress);
    assert.ok(next.active.some((entry) => entry.step === 'A'), 'legacy active projection stays unchanged');

    fs.writeFileSync(fixture.aMaterial, fixture.originalA);
    const started = cli('start', dir, {owner: 'parent', attempt: aClaim.attempt, context: context('planning-A')});
    assertProgressResponse(started, graph);
    const launched = cli('launched', dir, {owner: 'parent', attempt: aClaim.attempt, handle: 'planning-A'});
    assertProgressResponse(launched, graph);
    fs.writeFileSync(fixture.aMaterial, 'changed while running\n');
    next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    const runningA = row(progress, 'active', 'A');
    assert.equal(runningA.state, 'running');
    assert.equal(runningA.attempt, aClaim.attempt);
    assertOnlyAHasIssues(progress);

    const publication = publish(dir, started, 'SUCCEEDED');
    assertReceiptOnly(publication.report, 'planning receipt report');
    assertReceiptOnly(publication.receipt, 'planning receipt lookup');
    next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    const receiptA = row(progress, 'awaiting_verification', 'A');
    assert.equal(receiptA.state, 'receipt');
    assert.equal(receiptA.reported_status, 'SUCCEEDED');
    assertOnlyAHasIssues(progress);

    fs.writeFileSync(fixture.aMaterial, fixture.originalA);
    const settled = cli('settle', dir, {
      owner: 'parent',
      attempt: aClaim.attempt,
      verification: verification(publication.receipt, true, 'planning A accepted before later drift'),
    });
    assertProgressResponse(settled, graph);
    fs.writeFileSync(fixture.aMaterial, 'changed after acceptance\n');
    next = cli('next', dir);
    progress = assertProgressResponse(next, graph);
    const acceptedA = row(progress, 'completed', 'A');
    assert.equal(acceptedA.state, 'accepted');
    assert.equal(acceptedA.attempt, aClaim.attempt);
    assertOnlyAHasIssues(progress);
    assert.equal(row(progress, 'pending', 'B').dependency_ready, true);
    assert.equal(row(progress, 'pending', 'C').dependency_ready, true);
  });

  test('empty graphs remain rejected without a fabricated zero-total progress response', () => {
    const dir = path.join(root, 'empty-' + crypto.randomUUID());
    const failed = cli('init', dir, {owner: 'parent', graph: {version: 1, steps: []}}, true);
    assert.equal(Object.hasOwn(failed, 'progress'), false);
    assert.equal(fs.existsSync(dir), false);
    assert.match(failed.error, /graph|step|contract/i);
  });

  success = true;
  console.log(`plan-dispatcher-progress.test.js: ${count} groups passed (copied package, public CLI only)`);
} finally {
  if (success) {
    fs.rmSync(root, {recursive: true, force: true});
  } else {
    console.error('Retained failed dispatcher-progress fixtures: ' + root);
  }
}
