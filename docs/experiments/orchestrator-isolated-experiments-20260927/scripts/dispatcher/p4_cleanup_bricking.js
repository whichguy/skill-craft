'use strict';
// P4: after a rejected attempt, delete files the protocol says that attempt
// wrote (context.workspace dir, context.ready_evidence file, the reported
// result artifact, the verification evidence file), then try next/retry/
// packet/takeover/receipt and see which ones fail and why.
const fs = require('node:fs');
const path = require('node:path');
const lib = require('./lib');

const log = [];
function record(label, value) { log.push({label, value}); console.log('== ' + label + ' =='); console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2)); }

function rmrf(p) { try { fs.rmSync(p, {recursive: true, force: true}); } catch (e) { /* ignore */ } }

function tryCall(op, dir, input) {
  const r = lib.cli(op, dir, input);
  return {status: r.status, stderr: r.stderr.trim(), stdout_ok: r.status === 0};
}

// --- Scenario 1: rejected attempt, delete context.workspace + ready_evidence ---
{
  const {dir} = lib.initRun();
  const claimed = lib.cliOk('claim', dir, {owner: 'parent', steps: ['A']});
  const attempt = claimed.claims[0].attempt;
  const ctx = lib.context();
  const started = lib.cliOk('start', dir, {owner: 'parent', attempt, context: ctx});
  lib.cliOk('launched', dir, {owner: 'parent', attempt, handle: 'h-' + attempt});
  const packet = started.packet;
  fs.writeFileSync(packet.outputs.artifact, JSON.stringify({actual: 'bad'}));
  const envelope = {run_id: packet.run_id, step: packet.step, attempt, status: 'BLOCKED',
    evidence: {path: packet.outputs.artifact, sha256: lib.digest(fs.readFileSync(packet.outputs.artifact))}};
  lib.cliOk('report', dir, envelope);
  const settled = lib.settleFrom(dir, 'parent', attempt, envelope, {passed: false, reason: 'proven unachievable'});
  record('S1 settle outcome', settled.outcome);

  record('S1 baseline next() before deletion', tryCall('next', dir));

  record('S1 deleting context.workspace and ready_evidence.path', {workspace: ctx.workspace, ready_evidence: ctx.ready_evidence.path});
  rmrf(ctx.workspace);
  rmrf(ctx.ready_evidence.path);

  record('S1 next() after deleting workspace+ready_evidence', tryCall('next', dir));
  record('S1 packet() after deletion', tryCall('packet', dir, {attempt}));
  record('S1 receipt() after deletion', tryCall('receipt', dir, {attempt}));
  record('S1 retry() after deletion', tryCall('retry', dir, {owner: 'parent', attempt, confirmed_stopped: true, reason: 'old worker confirmed stopped'}));
  record('S1 takeover() after deletion', tryCall('takeover', dir, {oldOwner: 'parent', newOwner: 'parent2', confirmed_stopped: true, reason: 'switching owner'}));
  record('S1 describe (raw) after deletion', tryCall('next', dir)); // dispatch.js has no bare "describe" op; state.describe is internal only
}

// --- Scenario 2: rejected attempt, delete ONLY the reported result artifact (outputs.artifact) ---
{
  const {dir} = lib.initRun();
  const claimed = lib.cliOk('claim', dir, {owner: 'parent', steps: ['A']});
  const attempt = claimed.claims[0].attempt;
  const ctx = lib.context();
  const started = lib.cliOk('start', dir, {owner: 'parent', attempt, context: ctx});
  lib.cliOk('launched', dir, {owner: 'parent', attempt, handle: 'h-' + attempt});
  const packet = started.packet;
  fs.writeFileSync(packet.outputs.artifact, JSON.stringify({actual: 'bad'}));
  const envelope = {run_id: packet.run_id, step: packet.step, attempt, status: 'BLOCKED',
    evidence: {path: packet.outputs.artifact, sha256: lib.digest(fs.readFileSync(packet.outputs.artifact))}};
  lib.cliOk('report', dir, envelope);
  lib.settleFrom(dir, 'parent', attempt, envelope, {passed: false, reason: 'proven unachievable'});

  record('S2 deleting only outputs.artifact (result.json) for a REJECTED attempt', packet.outputs.artifact);
  rmrf(packet.outputs.artifact);
  record('S2 next() after deleting only result artifact (rejected, not accepted)', tryCall('next', dir));
  record('S2 retry() after deleting only result artifact', tryCall('retry', dir, {owner: 'parent', attempt, confirmed_stopped: true, reason: 'x'}));
}

// --- Scenario 3: ACCEPTED attempt, delete the accepted verification evidence file ---
{
  const {dir} = lib.initRun();
  const {attempt, envelope} = lib.driveToReport(dir, 'parent', 'A', {status: 'SUCCEEDED'});
  const rec = lib.cliOk('receipt', dir, {attempt});
  const verifEvidence = lib.evidence({actual: 42, passed: true});
  const verification = {receipt_sha256: rec.sha256, passed: true, reason: 'ok', evidence: verifEvidence};
  const settled = lib.cliOk('settle', dir, {owner: 'parent', attempt, verification});
  record('S3 settle outcome (should be accepted)', settled.outcome);
  record('S3 baseline next() before deletion', tryCall('next', dir));

  record('S3 deleting verification.evidence.path (accepted attempt)', verifEvidence.path);
  rmrf(verifEvidence.path);
  record('S3 next() after deleting accepted verification evidence', tryCall('next', dir));
  record('S3 packet-adjacent op: receipt() after deletion', tryCall('receipt', dir, {attempt}));
}

// --- Scenario 4: ACCEPTED attempt, delete the reported result artifact (accepted receipt evidence) ---
{
  const {dir} = lib.initRun();
  const {attempt, envelope, packet} = (() => {
    const claimed = lib.cliOk('claim', dir, {owner: 'parent', steps: ['A']});
    const at = claimed.claims[0].attempt;
    const ctx = lib.context();
    const started = lib.cliOk('start', dir, {owner: 'parent', attempt: at, context: ctx});
    lib.cliOk('launched', dir, {owner: 'parent', attempt: at, handle: 'h-' + at});
    const pk = started.packet;
    fs.writeFileSync(pk.outputs.artifact, JSON.stringify({actual: 42}));
    const env = {run_id: pk.run_id, step: pk.step, attempt: at, status: 'SUCCEEDED',
      evidence: {path: pk.outputs.artifact, sha256: lib.digest(fs.readFileSync(pk.outputs.artifact))}};
    lib.cliOk('report', dir, env);
    return {attempt: at, envelope: env, packet: pk};
  })();
  lib.settleFrom(dir, 'parent', attempt, envelope, {passed: true});
  record('S4 deleting outputs.artifact for an ACCEPTED attempt (result.json)', packet.outputs.artifact);
  rmrf(packet.outputs.artifact);
  record('S4 next() after deleting accepted receipt evidence', tryCall('next', dir));
}

fs.writeFileSync(path.join(__dirname, 'p4_output.json'), JSON.stringify(log, null, 2));
console.log('P4 DONE');
