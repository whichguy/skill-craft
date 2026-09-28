'use strict';
// P5: fire N=20 concurrent state-writing calls (claim, one per distinct step)
// against the same run directory, count ELOCKED failures. Then simulate an
// orphaned lock file (a process that acquired the lock and died before its
// finally-block unlink) and show whether later calls can ever recover
// without external intervention.
const fs = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const lib = require('./lib');

const log = [];
function record(label, value) { log.push({label, value}); console.log('== ' + label + ' =='); console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2)); }

const N = 20;
const steps = [];
for (let i = 0; i < N; i++) steps.push({id: 'S' + i, deps: [], contract: lib.contract('S' + i)});
const graph = {version: 1, steps};
const {dir} = lib.initRun(graph);
record('graph', `${N} independent steps, run dir ${dir}`);

function spawnClaim(stepId) {
  return new Promise(resolve => {
    const inputFile = lib.save({owner: 'parent', steps: [stepId]});
    const child = spawn(process.execPath, [lib.HELPER, 'claim', dir, inputFile], {cwd: lib.CWD});
    let stdout = '', stderr = '';
    child.stdout.on('data', d => stdout += d);
    child.stderr.on('data', d => stderr += d);
    child.on('close', code => resolve({stepId, code, stdout, stderr}));
  });
}

async function runConcurrentClaims() {
  const promises = steps.map(s => spawnClaim(s.id));
  const results = await Promise.all(promises);
  const ok = results.filter(r => r.code === 0);
  const failed = results.filter(r => r.code !== 0);
  const elocked = failed.filter(r => {
    try { return JSON.parse(r.stderr).code === 'ELOCKED'; } catch (_) { return false; }
  });
  const otherFailures = failed.filter(r => !elocked.includes(r));
  record('P5 concurrent claim results: ok count', ok.length);
  record('P5 concurrent claim results: failed count', failed.length);
  record('P5 concurrent claim results: ELOCKED count', elocked.length);
  record('P5 concurrent claim results: other-failure count', otherFailures.length);
  record('P5 sample ELOCKED error', elocked[0] ? elocked[0].stderr.trim() : null);
  record('P5 sample other failure (if any)', otherFailures[0] ? otherFailures[0].stderr.trim() : null);

  // Verify state integrity: total claims actually recorded should equal ok.length,
  // and each ok result corresponds to a distinct claimed step (no double-claim / corruption).
  const nextResp = lib.cliOk('next', dir);
  const claimedSteps = nextResp.active.map(a => a.step);
  record('P5 steps actually claimed after the storm', claimedSteps.length);
  record('P5 claimed-count matches ok-count (no silent loss/corruption)?', claimedSteps.length === ok.length);
  return {ok, failed, elocked};
}

async function main() {
  const {failed} = await runConcurrentClaims();

  // --- Orphan lock simulation ---
  const {dir: dir2} = lib.initRun({version: 1, steps: [{id: 'X', deps: [], contract: lib.contract('X')}]});
  const lockPath = path.join(dir2, '.dispatcher.lock');
  record('P5 orphan-lock scenario: run dir', dir2);
  // Simulate a crashed dispatcher process: it opened the lock (wx) and wrote
  // its pid, then died before the finally-block's unlinkSync ran.
  fs.writeFileSync(lockPath, String(999999), {flag: 'wx'});
  record('P5 orphan lock file created (simulating a dead PID)', fs.readFileSync(lockPath, 'utf8'));

  const afterOrphan = lib.cli('claim', dir2, {owner: 'parent', steps: ['X']});
  record('P5 claim() with orphan lock present', {status: afterOrphan.status, stderr: afterOrphan.stderr.trim()});
  const afterOrphanNext = lib.cli('next', dir2); // next() is read-only, does not take the lock
  record('P5 next() (read-only) with orphan lock present -- does read-only work bypass the lock?', {status: afterOrphanNext.status, stderr: afterOrphanNext.stderr.trim()});
  const afterOrphanRetry = lib.cli('retry', dir2, {owner: 'parent', attempt: 'nonexistent', confirmed_stopped: true, reason: 'x'});
  record('P5 retry() with orphan lock present (also a write, also fails)', {status: afterOrphanRetry.status, stderr: afterOrphanRetry.stderr.trim()});

  // Is there ANY CLI operation that clears a stale lock, or a staleness/PID-liveness check?
  record('P5 does dispatch.js CLI expose any lock-clearing/staleness operation?', 'checked operation list in dispatch.js switch: capabilities, validate-graph, init, next, claim, start, check-context, packet, launched, report, receipt, settle, retry, takeover -- none inspect or clear .dispatcher.lock; only fs-level access (manual unlink) can recover.');

  // Confirm manual unlink recovers it (proving the lock has no other recovery path).
  fs.unlinkSync(lockPath);
  const afterManualUnlink = lib.cli('claim', dir2, {owner: 'parent', steps: ['X']});
  record('P5 claim() after manually deleting the orphan lock file (only recovery path found)', {status: afterManualUnlink.status});

  fs.writeFileSync(path.join(__dirname, 'p5_output.json'), JSON.stringify(log, null, 2));
  console.log('P5 DONE');
}

main().catch(e => { console.error(e); process.exit(1); });
