'use strict';
// P6: is there any capacity input at init? Is serial capacity 1 enforced in
// code? Are planning-blocked steps still offered for claim (and does claim
// itself succeed on them, with enforcement deferred to start())?
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const lib = require('./lib');

const log = [];
function record(label, value) { log.push({label, value}); console.log('== ' + label + ' =='); console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2)); }

// --- 6a: does init accept any capacity-ish field? ---
{
  const dir = lib.newRunDir();
  const attempt = lib.cli('init', dir, {owner: 'parent', graph: lib.neutralGraph(), capacity: 1, serial_capacity: 1, max_concurrency: 1});
  record('6a init with extra capacity/serial_capacity/max_concurrency fields', {status: attempt.status, stderr: attempt.stderr.trim()});
}

// --- 6b: does a single claim() call let you claim ALL ready steps in one shot (no cap)? ---
{
  const N = 10;
  const steps = [];
  for (let i = 0; i < N; i++) steps.push({id: 'P' + i, deps: [], contract: lib.contract('P' + i)});
  const {dir} = lib.initRun({version: 1, steps});
  const allIds = steps.map(s => s.id);
  const claimed = lib.cliOk('claim', dir, {owner: 'parent', steps: allIds});
  record('6b single claim() call for ' + N + ' independent ready steps at once', {requested: N, claimed: claimed.claims.length, claimedSteps: claimed.claims.map(c => c.step)});
  record('6b conclusion', claimed.claims.length === N ? 'no code-level cap: all N claimed in one call, no serial-capacity-1 enforcement' : 'unexpected cap observed');
}

// --- 6c: planning-blocked step -- is it still offered in ready[]/claim action, and does claim() itself succeed on it? ---
{
  function digest(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
  function save(value, ext = '.json') { const f = path.join(lib.ROOT, crypto.randomUUID() + ext); fs.writeFileSync(f, typeof value === 'string' ? value : JSON.stringify(value)); return f; }
  function reference(file) { return {path: file, sha256: digest(fs.readFileSync(file))}; }

  const inputGraph = {version: 1, steps: [
    {id: 'B', deps: [], contract: lib.contract('B')},
    {id: 'C', deps: [], contract: lib.contract('C')},
  ]};
  const graphFile = save(inputGraph);
  const brief = save('# brief\n', '.md');
  const bMaterial = save('B planning material\n', '.md');
  const artifacts = [
    {...reference(brief), roles: ['planning-brief'], producers: ['planning-context'], classification: 'current', required_for: ['*']},
    {...reference(bMaterial), roles: ['requirements'], producers: ['spec-1'], classification: 'current', required_for: ['B']},
  ];
  const manifest = {schema: 'shiploop-planning-artifacts/v1', source: {run_id: 'r', action_id: 'a', workitem: 'w', revision: 1}, graph: reference(graphFile), briefing: reference(brief), artifacts, unresolved_refs: [], reference_only: []};
  const manifestFile = save(manifest);
  const planning_context = {...reference(manifestFile), source: {run_id: 'r', action_id: 'a'}};

  const dir = lib.newRunDir();
  const view = lib.cliOk('init', dir, {owner: 'parent', graph: inputGraph, planning_context});
  record('6c init view before drift: planning_blocked_steps', view.planning_blocked_steps);

  // Drift B's planning material so its hash no longer matches the manifest.
  fs.writeFileSync(bMaterial, 'CHANGED B planning material\n');

  const afterDrift = lib.cliOk('next', dir);
  record('6c next() after drifting B material: planning_blocked_steps', afterDrift.planning_blocked_steps);
  record('6c next() after drift: is B still in ready[]?', afterDrift.ready.includes('B'));
  const claimAction = afterDrift.actions.find(a => a.action === 'claim');
  record('6c claim action steps (does it include the planning-blocked B)?', claimAction ? claimAction.steps : null);
  const advisoryAction = afterDrift.actions.find(a => a.action === 'inspect-planning-context' && a.steps);
  record('6c separate inspect-planning-context advisory action', advisoryAction);

  // Does claim() itself succeed for the planning-blocked step B (enforcement deferred to start)?
  const claimResult = lib.cli('claim', dir, {owner: 'parent', steps: ['B']});
  record('6c claim() call directly targeting the planning-blocked step B', {status: claimResult.status, claimed: claimResult.json && claimResult.json.claims});

  // Confirm start() is where enforcement actually happens.
  if (claimResult.status === 0) {
    const attempt = claimResult.json.claims[0].attempt;
    const startResult = lib.cli('start', dir, {owner: 'parent', attempt, context: lib.context()});
    record('6c start() on the claimed-but-planning-blocked attempt', {status: startResult.status, stderr: startResult.stderr.trim()});
  }
}

fs.writeFileSync(path.join(__dirname, 'p6_output.json'), JSON.stringify(log, null, 2));
console.log('P6 DONE');
