'use strict';
// P3: across a full walk (A, B deps A, C independent -> completion), record
// every distinct next_argv / report_argv / any argv used, and separately
// count every protocol call whose op+input we had to compose ourselves
// (no literal argv was returned for it), listing fields no prior response
// carried (e.g. receipt_sha256, context.*, verification.*, handle).
const fs = require('node:fs');
const path = require('node:path');
const lib = require('./lib');

const calls = []; // {op, composedBy: 'returned-argv'|'caller', inputFieldsCallerSupplied: [...]}
const distinctArgvShapes = new Set();

function noteArgv(source, argv) {
  const shape = argv.slice(1).map(x => (typeof x === 'string' && x.startsWith('/')) ? '<path>' : x).join(' ');
  distinctArgvShapes.add(`[${source}] ${shape}`);
}

const {dir} = lib.initRun();
calls.push({op: 'init', composedBy: 'caller (first call, nothing to return it)', fieldsCallerSupplied: ['graph (full contract text)', 'owner']});

let r = lib.cliOk('next', dir);
noteArgv('next response', r.next_argv);

function claimStep(step) {
  const claimed = lib.cliOk('claim', dir, {owner: 'parent', steps: [step]});
  calls.push({op: 'claim', composedBy: 'caller', fieldsCallerSupplied: ['owner', 'steps (chosen from ready[] list, but op+shape not returned as argv)']});
  noteArgv('claim response', claimed.next_argv);
  return claimed.claims[0].attempt;
}

function startAttempt(attempt) {
  const ctx = lib.context();
  const started = lib.cliOk('start', dir, {owner: 'parent', attempt, context: ctx});
  calls.push({op: 'start', composedBy: 'caller', fieldsCallerSupplied: ['owner', 'context.workspace', 'context.write_scope', 'context.resources', 'context.ready_evidence.{path,sha256} (caller-authored evidence file + its own hash)']});
  noteArgv('start response', started.next_argv);
  return started;
}

function launchAttempt(attempt) {
  const handle = 'fixture-' + attempt;
  const launched = lib.cliOk('launched', dir, {owner: 'parent', attempt, handle});
  calls.push({op: 'launched', composedBy: 'caller', fieldsCallerSupplied: ['owner', 'handle (opaque native-launch identity; never returned by any prior call)']});
  noteArgv('launched response', launched.next_argv);
  return launched;
}

function reportAttempt(packet) {
  fs.writeFileSync(packet.outputs.artifact, JSON.stringify({actual: 42}));
  const envelope = {
    run_id: packet.run_id, step: packet.step, attempt: packet.attempt,
    status: 'SUCCEEDED',
    evidence: {path: packet.outputs.artifact, sha256: lib.digest(fs.readFileSync(packet.outputs.artifact))},
  };
  noteArgv('packet.report_argv', packet.report_argv);
  calls.push({op: 'report', composedBy: 'returned-argv (op+dir+envelope-path from packet.report_argv)', fieldsCallerSupplied: ['envelope.status (worker judgment)', 'envelope.evidence.sha256 (worker computes)']});
  const reported = lib.cliOk('report', dir, envelope);
  noteArgv('report response', reported.next_argv);
  return {envelope, reported};
}

function settleAttempt(attempt, envelope) {
  const rec = lib.cliOk('receipt', dir, {attempt});
  calls.push({op: 'receipt', composedBy: 'caller', fieldsCallerSupplied: ['attempt (must remember it; no argv returned)']});
  noteArgv('receipt response', rec.next_argv);
  const verification = {receipt_sha256: rec.sha256, passed: true, reason: 'Independent fixture inspection', evidence: lib.evidence({actual: 42, passed: true})};
  calls.push({op: 'settle', composedBy: 'caller', fieldsCallerSupplied: ['owner', 'verification.receipt_sha256 (obtained via separate receipt() call)', 'verification.passed (verifier judgment)', 'verification.reason (verifier-authored)', 'verification.evidence.{path,sha256} (verifier-authored file + its own hash)']});
  const settled = lib.cliOk('settle', dir, {owner: 'parent', attempt, verification});
  noteArgv('settle response', settled.next_argv);
  return settled;
}

function driveStep(step) {
  const attempt = claimStep(step);
  const started = startAttempt(attempt);
  launchAttempt(attempt);
  const packet = started.packet;
  const {envelope} = reportAttempt(packet);
  return settleAttempt(attempt, envelope);
}

// A has no deps -> ready immediately. C also ready immediately.
driveStep('A');
driveStep('C');
r = lib.cliOk('next', dir);
noteArgv('next response', r.next_argv);
// Now B should be ready (dep A accepted).
driveStep('B');
r = lib.cliOk('next', dir);
noteArgv('next response (terminal)', r.next_argv);

const summary = {
  distinct_argv_shapes: Array.from(distinctArgvShapes).sort(),
  total_protocol_calls: calls.length,
  calls_using_a_returned_argv: calls.filter(c => c.composedBy.startsWith('returned-argv')).length,
  calls_caller_had_to_compose: calls.filter(c => !c.composedBy.startsWith('returned-argv')).length,
  calls_detail: calls,
  terminal_complete: r.complete,
};
fs.writeFileSync(path.join(__dirname, 'p3_output.json'), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
console.log('P3 DONE');
