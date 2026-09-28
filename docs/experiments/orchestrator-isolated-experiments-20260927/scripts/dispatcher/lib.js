'use strict';
// Shared black-box harness for Plan Dispatcher CLI probes.
// Talks ONLY to the snapshotted dispatch.js via child_process, like a real caller would.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');

const SRC = path.resolve(__dirname, '..', 'src');
const HELPER = path.join(SRC, 'skills', 'plan-dispatcher', 'scripts', 'dispatch.js');
const ROOT = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'dispatcher-probe-')));
const CWD = path.join(ROOT, 'cwd'); // never the run dir itself
fs.mkdirSync(CWD, {recursive: true});
const STATE_FILE = 'plan-dispatcher-state.json';

function digest(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
function save(value) {
  const file = path.join(ROOT, crypto.randomUUID() + '.json');
  fs.writeFileSync(file, JSON.stringify(value));
  return file;
}
function evidence(value) {
  const file = save(value);
  return {path: file, sha256: digest(fs.readFileSync(file))};
}

// Raw CLI invocation. Returns {status, stdout, stderr, json} (json parsed from
// stdout on success, from stderr on failure).
function cli(op, run, input) {
  let inputFile;
  if (input !== undefined) {
    if (op === 'report') {
      inputFile = path.join(run, 'artifacts', input.attempt, 'envelope.json');
      fs.writeFileSync(inputFile, JSON.stringify(input));
    } else {
      inputFile = save(input);
    }
  }
  const argv = [HELPER, op, run, ...(inputFile === undefined ? [] : [inputFile])];
  const child = spawnSync(process.execPath, argv, {cwd: CWD, encoding: 'utf8', timeout: 15000});
  const out = {
    status: child.status,
    signal: child.signal,
    stdout: child.stdout,
    stderr: child.stderr,
    argv: [process.execPath, ...argv],
  };
  try { out.json = JSON.parse(child.status === 0 ? child.stdout : child.stderr); } catch (_) { out.json = null; }
  return out;
}

// Convenience wrapper that throws on failure (mirrors the "happy path" callers use).
function cliOk(op, run, input) {
  const r = cli(op, run, input);
  if (r.status !== 0) {
    throw new Error(`cli ${op} failed: ${r.stderr}`);
  }
  return r.json;
}

function contract(id) {
  return {task: `Implement ${id}`, ready: [`Inputs for ${id} verified`], done: [`${id} independently checked`]};
}
// Neutral graph: A (no deps), B (deps A), C (independent).
function neutralGraph() {
  return {
    version: 1,
    steps: [
      {id: 'A', deps: [], contract: contract('A')},
      {id: 'B', deps: ['A'], contract: contract('B')},
      {id: 'C', deps: [], contract: contract('C')},
    ],
  };
}

const RUNS_DIR = path.join(ROOT, 'runs');
fs.mkdirSync(RUNS_DIR, {recursive: true});
function newRunDir() { return path.join(RUNS_DIR, crypto.randomUUID()); }

function initRun(graph = neutralGraph(), owner = 'parent') {
  const dir = newRunDir();
  const view = cliOk('init', dir, {owner, graph});
  return {dir, view};
}

function context() {
  const workspace = path.join(ROOT, crypto.randomUUID());
  fs.mkdirSync(workspace, {recursive: true});
  return {workspace, write_scope: ['result.txt'], resources: [], ready_evidence: evidence({checked: true})};
}

// Drive one claimed step from claim() through report(), returning enough to settle.
function driveToReport(dir, owner, step, {status = 'SUCCEEDED', body = {actual: 42}} = {}) {
  const claimed = cliOk('claim', dir, {owner, steps: [step]});
  const attempt = claimed.claims[0].attempt;
  const started = cliOk('start', dir, {owner, attempt, context: context()});
  const handle = 'fixture-' + attempt;
  cliOk('launched', dir, {owner, attempt, handle});
  const packet = started.packet;
  fs.writeFileSync(packet.outputs.artifact, JSON.stringify(body));
  const envelope = {
    run_id: packet.run_id, step: packet.step, attempt,
    status,
    evidence: {path: packet.outputs.artifact, sha256: digest(fs.readFileSync(packet.outputs.artifact))},
  };
  const reportResp = cliOk('report', dir, envelope);
  return {attempt, packet, envelope, reportResp};
}

function settleFrom(dir, owner, attempt, envelope, {passed = true, reason = 'Independent fixture inspection'} = {}) {
  // receipt_sha256 must match the durable inbox bytes; fetch via receipt().
  const rec = cliOk('receipt', dir, {attempt});
  const verif = {receipt_sha256: rec.sha256, passed, reason, evidence: evidence({actual: 42, passed})};
  return cliOk('settle', dir, {owner, attempt, verification: verif});
}

module.exports = {
  SRC, HELPER, ROOT, CWD, STATE_FILE,
  digest, save, evidence, cli, cliOk,
  contract, neutralGraph, newRunDir, initRun, context, driveToReport, settleFrom,
};
