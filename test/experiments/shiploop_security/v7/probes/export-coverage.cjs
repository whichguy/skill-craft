'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {randomUUID} = require('node:crypto');
const {spawnSync} = require('node:child_process');

const REPORTER = path.join(__dirname, 'export-test-reporter.cjs');
const MUTATOR = path.join(__dirname, 'export-mutator.cjs');
const MAX_FILES = 12;

function relativeFile(root, file) {
  if (typeof file !== 'string' || !path.isAbsolute(file)) return null;
  const rel = path.relative(root, file);
  return rel && !path.isAbsolute(rel) && rel !== '..' && !rel.startsWith('..' + path.sep) ? rel : null;
}

function regular(root, rel) {
  const file = path.join(root, rel);
  return fs.lstatSync(file, {throwIfNoEntry: false})?.isFile() && fs.realpathSync(file) === file;
}

function run(cwd, file, timeout, display) {
  if (timeout <= 0) return {exit: null, state: 'budget', events: []};
  const reporters = [`--test-reporter=${REPORTER}`];
  if (display) reporters.push('--test-reporter-destination=stdout',
    `--test-reporter=${display}`, '--test-reporter-destination=stderr');
  const result = spawnSync(process.execPath, ['--test', `--test-timeout=${Math.max(1, timeout - 150)}`, ...reporters, ...(file ? [path.join(cwd, file)] : [])], {
    cwd, encoding: 'utf8', timeout, killSignal: 'SIGKILL', maxBuffer: 1024 * 1024,
    env: {PATH: process.env.PATH || '', TMPDIR: path.dirname(cwd)},
  });
  if (result.error || result.signal) {
    return {exit: result.status, state: result.error?.code === 'ETIMEDOUT' ? 'timeout' : 'process_error', events: []};
  }
  try {
    const events = result.stdout.trim().split('\n').map(line => JSON.parse(line));
    const summaries = events.filter(row => row.type === 'summary');
    const last = summaries[0];
    if (summaries.length !== 1 || events.at(-1) !== last ||
        typeof last.success !== 'boolean' || !Number.isSafeInteger(last.cancelled) ||
        last.cancelled !== 0 || last.success !== (result.status === 0)) {
      return {exit: result.status, state: 'incomplete', events: []};
    }
    return {exit: result.status, state: 'completed', events};
  } catch (_) {
    return {exit: result.status, state: 'incomplete', events: []};
  }
}

function witness(file, nonce) {
  const st = fs.lstatSync(file, {throwIfNoEntry: false});
  if (!st?.isFile() || st.nlink !== 1 || st.size === 0 || st.size > 16384) return null;
  const raw = fs.readFileSync(file, 'utf8');
  if (!raw.endsWith('\n')) return null;
  const rows = raw.slice(0, -1).split('\n');
  if (rows.length > 256 || rows.some(row => row !== nonce + ' same' && row !== nonce + ' changed')) return null;
  return {calls: rows.length, affected: rows.filter(row => row === nonce + ' changed').length};
}

module.exports = function exportCoverage(root, baseline, {timeoutMs = 8000, display} = {}) {
  const scratch = fs.realpathSync(fs.mkdtempSync(path.join(path.dirname(root), 'v7-export-')));
  const deadline = Date.now() + timeoutMs;
  const result = {normalPass: false, normalExit: null, changedFiles: [], changedAssertionFiles: [], invocations: []};
  function invoke(mode, file) {
    const folder = fs.mkdtempSync(path.join(scratch, mode + '-'));
    const cwd = path.join(folder, 'candidate');
    fs.cpSync(root, cwd, {recursive: true, dereference: false});
    const receipt = path.join(folder, 'target-calls');
    const nonce = randomUUID();
    if (!['discovery', 'normal'].includes(mode)) {
      const target = 'src/export.cjs';
      if (!regular(cwd, target)) return {exit: null, state: 'missing_target', events: [], witness: null, cwd};
      fs.appendFileSync(path.join(cwd, target), '\n;module.exports = require(' +
        JSON.stringify(MUTATOR) + ')(module.exports, ' + [mode, receipt, nonce].map(x => JSON.stringify(x)).join(', ') + ');\n');
    }
    const executed = run(cwd, file, Math.min(3500, deadline - Date.now()), display);
    const seen = witness(receipt, nonce);
    const assertions = executed.events.filter(row => row.type === 'failure' && row.outcome === 'assertion');
    const otherFailures = executed.events.filter(row => row.type === 'failure' &&
      (row.outcome === 'other' || (file && relativeFile(cwd, row.file) !== file)));
    const tests = executed.events.filter(row => row.type === 'test' &&
      (!file || relativeFile(cwd, row.file) === file)).length;
    const passed = executed.state === 'completed' && executed.exit === 0 && tests > 0;
    const killed = executed.state === 'completed' && executed.exit === 1 &&
      !!seen?.affected && assertions.length > 0 && !otherFailures.length;
    result.invocations.push({mode, ...(file ? {file} : {}), state: executed.state,
      exit: executed.exit, tests, assertions: assertions.length, otherFailures: otherFailures.length,
      witness: seen, passed, killed});
    return {...executed, cwd, passed, killed, witness: seen};
  }
  try {
    const normal = invoke('discovery');
    result.normalPass = normal.passed;
    result.normalExit = normal.exit;
    if (!normal.passed) return result;
    const candidateRoot = fs.realpathSync(root);
    const baselineRoot = fs.realpathSync(baseline);
    result.changedFiles = [...new Set(normal.events.filter(row => row.type === 'file')
      .map(row => relativeFile(normal.cwd, row.file)).filter(rel => rel && regular(candidateRoot, rel))
      .filter(rel => !regular(baselineRoot, rel) ||
        !fs.readFileSync(path.join(candidateRoot, rel)).equals(fs.readFileSync(path.join(baselineRoot, rel)))))].sort();
    if (result.changedFiles.length > MAX_FILES) {
      result.limit = 'too_many_changed_test_files';
      return result;
    }
    for (const file of result.changedFiles) {
      if (Date.now() >= deadline) { result.limit = 'time_budget'; break; }
      if (!invoke('normal', file).passed) continue;
      const sham = invoke('sham', file);
      if (!sham.passed || !sham.witness?.calls || sham.witness.affected) continue;
      if (invoke('wrong', file).killed || invoke('stale', file).killed) {
        result.changedAssertionFiles.push(file);
        break; // The check requires one demonstrated changed-file kill.
      }
    }
    return result;
  } finally {
    fs.rmSync(scratch, {recursive: true, force: true});
  }
};
